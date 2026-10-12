"""Exercise shipped slider callbacks and the real settings model across float32 UI values."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import unittest

from lupa.lua54 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[2]
SCRIPTS = ROOT / "Mods/CabinModSettings/Scripts"
DEFINITIONS = ROOT / "tests/fixtures/slider-definitions"
FAST = DEFINITIONS / "fast.lua"
SHORT = DEFINITIONS / "short.lua"
CHAIR = DEFINITIONS / "chair.lua"


def definition_source_checks():
    comparisons = []
    for name, fixture in (("CabinFastTurns", FAST), ("CabinShortEvents", SHORT), ("CabinChairMarker", CHAIR)):
        source = WORKSPACE / "mods" / name / "repository/Mods" / name / "Scripts/definition.lua"
        if source.is_file():
            if fixture.read_bytes() != source.read_bytes():
                raise AssertionError(f"slider definition fixture differs from workspace source: {name}")
            status = "byte-identical"
            print(f"info: slider definition fixture matches workspace source: {name}")
        else:
            status = "optional workspace comparison skipped; repository fixture remains active"
            print(f"info: optional slider source comparison skipped: {name} sibling repository absent; all callback cases use repository fixtures")
        comparisons.append({"mod": name, "fixture": str(fixture), "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(), "workspace_source": str(source), "comparison": status})
    return comparisons

FIXTURE = r'''
package.path=scripts.."/?.lua;"..package.path
local codec=require("cabin_codec")
local storage=require("cabin_store")
definitions={assert(loadfile(fast_definition))(),assert(loadfile(short_definition))(),assert(loadfile(chair_definition))()}
saved,revisions,requests,responses={},{},{},{}
for _,definition in ipairs(definitions) do
    saved[definition.id]=storage.defaults(definition.fields)
    revisions[definition.id]=1
end
registry={}
function registry:list()
    local result={}
    for _,definition in ipairs(definitions) do
        result[#result+1]={definition=codec.copy(definition),values=codec.copy(saved[definition.id]),revision=revisions[definition.id]}
    end
    return result
end
function registry:request(id,token,revision,values,action)
    assert(revision==revisions[id],"fixture request revision differs")
    requests[#requests+1]={id=id,token=token,values=codec.copy(values),action=action}
    saved[id]=codec.copy(values)
    revisions[id]=revision+1
    responses[token]={ok=true,values=codec.copy(values),revision=revisions[id]}
end
function registry:response(_,token) return responses[token] end

local next_address=0
local function widget()
    next_address=next_address+1
    local value={address=next_address,visible=true,viewport=true}
    function value:GetAddress() return self.address end
    function value:IsVisible() return self.visible end
    function value:IsInViewport() return self.viewport end
    function value:RemoveFromParent() self.viewport=false end
    function value:SetFont(font) self.font=font end
    function value:SetAutoWrapText(enabled) self.auto_wrap=enabled end
    function value:SetIsEnabled(enabled) self.enabled=enabled end
    return value
end
local function slider()
    local value=widget()
    value.sets,value.gets=0,0
    function value:SetMinValue(minimum) self.minimum=float32(minimum) end
    function value:SetMaxValue(maximum) self.maximum=float32(maximum) end
    function value:SetStepSize(step) self.step=float32(step) end
    function value:SetValue(number) self.sets=self.sets+1;self.value=float32(number)+(self.setter_error or 0) end
    function value:GetValue() self.gets=self.gets+1;return self.value end
    function value:drag(number)
        self.value=math.max(self.minimum,math.min(self.maximum,float32(number)))
    end
    function value:mouse(number)
        assert(self.MouseUsesStep==true,"native mouse step disabled")
        self:drag(math.floor(number/self.step+0.5)*self.step)
    end
    return value
end
local ui={}
function ui.valid(value) return value~=nil and value.valid~=false end
function ui.text(value,text) value.text=text end
function ui.native(class)
    assert(class=="TextBlock","unexpected native fixture widget: "..class)
    return widget()
end
function ui.create(class)
    local row=widget()
    row.SlotTitle_T=widget()
    if class:find("CabinNumberRow",1,true) then
        row.Slider=slider();row.SliderAmount=widget()
    elseif class:find("CabinBoolRow",1,true) then
        row.CheckBox_129=widget()
        function row.CheckBox_129:SetIsChecked(value) self.checked=value end
    elseif class:find("CabinChoiceRow",1,true) then
        row.OptionType_T=widget()
    else error("unexpected fixture row: "..class) end
    return row
end
package.loaded.ui=ui
callbacks,observers,logs={},{},{}
local mod={registry=registry}
function mod:bind(path,callback) callbacks[path]=callback end
function mod:observe(name,callback) observers[name]=callback end
function mod:log(level,message) logs[#logs+1]={level=level,message=message} end
panel=assert(loadfile(scripts.."/settings_panel.lua"))().start(mod,scripts.."/")
panel.mode="settings"
panel.widget=widget();panel.widget.WidgetTree={}
panel.content={children={}}
function panel.content:ClearChildren() self.children={} end
function panel.content:AddChildToVerticalBox(value)
    self.children[#self.children+1]=value
    return {SetPadding=function(_,padding) value.padding=padding end}
end
panel.model:open()

function select_mod(id) panel:select(id) end
function number_row(key)
    for _,record in pairs(panel.rows) do
        if record.role=="number" and record.field.key==key then return record end
    end
    error("number row missing: "..key)
end
local names={
    apply="BndEvt__CabinSettingsPanel_Apply_B_K2Node_ComponentBoundEvent_13_OnButtonPressedEvent__DelegateSignature",
    cancel="BndEvt__CabinSettingsPanel_Cancel_B_K2Node_ComponentBoundEvent_12_OnButtonPressedEvent__DelegateSignature",
    defaults="BndEvt__CabinSettingsPanel_Apply_B_1_K2Node_ComponentBoundEvent_3_OnButtonPressedEvent__DelegateSignature",
}
function click(name)
    local current=panel.widget
    local context={get=function() return current end}
    local path="/Game/CabinModSettings/CabinSettingsPanel.CabinSettingsPanel_C:"..assert(names[name])
    assert(callbacks[path],"actual callback missing")(context)
end
function tick() assert(observers["settings acknowledgement"])() end
'''


class SliderBehavior(unittest.TestCase):
    def setUp(self):
        self.vm = LuaRuntime(unpack_returned_tuples=True)
        self.vm.globals().float32 = lambda value: struct.unpack("f", struct.pack("f", value))[0]
        self.vm.globals().scripts = SCRIPTS.as_posix()
        self.vm.globals().fast_definition = FAST.as_posix()
        self.vm.globals().short_definition = SHORT.as_posix()
        self.vm.globals().chair_definition = CHAIR.as_posix()
        self.vm.execute(FIXTURE)

    def test_initial_float32_does_not_dirty_exact_fraction(self):
        self.vm.execute(r'''
        select_mod("cabin_short_events")
        local record=number_row("balloon_factor")
        assert(record.widget.Slider:GetValue()~=2/3,"fixture did not model native float32")
        panel:stageNumbers();tick();panel:stageNumbers()
        local draft=panel.model.drafts.cabin_short_events
        assert(draft.values.balloon_factor==2/3 and draft.values.train_factor==2/3)
        assert(not draft.dirty and #requests==0)
        assert(record.widget.SliderAmount.text=="67 %")
        assert(record.widget.Slider.sets==1,"unmoved fraction was quantized")
        click("apply")
        assert(#requests==0,"unchanged float32 control caused a save")
        ''')

    def test_drag_percent_and_apply_dispatch_once(self):
        self.vm.execute(r'''
        select_mod("cabin_short_events")
        local record=number_row("balloon_factor")
        record.widget.Slider:drag(0.4)
        panel:stageNumbers()
        assert(panel.model.drafts.cabin_short_events.values.balloon_factor==0.4)
        assert(record.widget.SliderAmount.text=="40 %")
        click("apply")
        assert(#requests==1 and requests[1].values.balloon_factor==0.4)
        tick();click("apply")
        assert(#requests==1,"acknowledged unchanged draft was saved twice")
        ''')

    def test_cancel_discards_drag_without_registry_request(self):
        self.vm.execute(r'''
        select_mod("cabin_fast_turns")
        number_row("speed").widget.Slider:drag(3)
        panel:stageNumbers()
        assert(panel.model.drafts.cabin_fast_turns.values.speed==3)
        click("cancel")
        assert(not panel.model.visible and next(panel.model.drafts)==nil)
        assert(#requests==0 and saved.cabin_fast_turns.speed==2)
        panel.model:open()
        assert(panel.model.drafts.cabin_fast_turns.values.speed==2)
        ''')

    def test_defaults_skip_stale_control_and_render_exact_defaults(self):
        self.vm.execute(r'''
        select_mod("cabin_short_events")
        local old=number_row("balloon_factor")
        old.widget.Slider:drag(0.4);panel:stageNumbers()
        click("defaults")
        assert(panel.selection_requested.id=="cabin_short_events")
        old.widget.Slider:drag(0.5);panel:stageNumbers()
        assert(panel.model.drafts.cabin_short_events.values.balloon_factor==2/3)
        assert(#requests==0,"Defaults wrote before Apply")
        tick()
        local current=number_row("balloon_factor")
        assert(current.widget:GetAddress()~=old.widget:GetAddress())
        panel:stageNumbers()
        assert(panel.model.drafts.cabin_short_events.values.balloon_factor==2/3)
        assert(current.widget.SliderAmount.text=="67 %")
        click("apply")
        assert(#requests==1 and requests[1].values.balloon_factor==2/3)
        ''')

    def test_actual_definition_validators_and_fast_endpoints(self):
        self.vm.execute(r'''
        local storage=require("cabin_store")
        for _,definition in ipairs(definitions) do
            local values=storage.defaults(definition.fields)
            for _,field in ipairs(definition.fields) do
                if field.type=="number" then
                    if definition.id=="cabin_fast_turns" then assert(field.min==1 and field.max==5)
                    elseif definition.id=="cabin_chair_marker" then assert(field.min==5 and field.max==30)
                    else assert(field.min==0.01 and field.max==1) end
                    for _,bound in ipairs({field.min,field.max}) do
                        local candidate=require("cabin_codec").copy(values)
                        candidate[field.key]=bound
                        assert(storage.validate(definition.fields,candidate))
                    end
                    for _,bad in ipairs({field.min-0.001,field.max+0.001}) do
                        local candidate=require("cabin_codec").copy(values)
                        candidate[field.key]=bad
                        assert(not pcall(storage.validate,definition.fields,candidate))
                    end
                end
            end
        end
        select_mod("cabin_fast_turns")
        local record=number_row("speed")
        assert(record.widget.Slider.minimum==1 and record.widget.Slider.maximum==5)
        record.widget.Slider:drag(1);click("apply");tick()
        assert(saved.cabin_fast_turns.speed==1)
        record.widget.Slider:drag(5);click("apply");tick()
        assert(saved.cabin_fast_turns.speed==5 and #requests==2)
        ''')

    def test_short_slider_minimum_can_be_applied(self):
        self.vm.execute(r'''
        select_mod("cabin_short_events")
        local record=number_row("balloon_factor")
        record.widget.Slider:drag(0.01)
        click("apply")
        assert(panel.model.error==nil,"native minimum rejected: "..tostring(panel.model.error))
        assert(#requests==1,"native minimum did not dispatch")
        assert(saved.cabin_short_events.balloon_factor>=0.01)
        ''')

    def test_turns_and_chair_use_real_integer_steps_and_saved_values(self):
        self.vm.execute(r'''
        select_mod("cabin_fast_turns")
        local turn=number_row("speed")
        assert(turn.widget.Slider.step==1 and turn.widget.Slider.MouseUsesStep==true)
        turn.widget.Slider:drag(3.49);panel:stageNumbers()
        assert(turn.widget.Slider:GetValue()==3 and turn.widget.SliderAmount.text=="3")
        assert(panel.model.drafts.cabin_fast_turns.values.speed==3)
        local sets=turn.widget.Slider.sets
        panel:stageNumbers();tick();panel:stageNumbers()
        assert(turn.widget.Slider.sets==sets,"stable snapped value was set repeatedly")
        turn.widget.Slider:drag(3.51);click("apply");tick()
        assert(saved.cabin_fast_turns.speed==4 and #requests==1)
        select_mod("cabin_chair_marker")
        local chair=number_row("size")
        assert(chair.widget.Slider.minimum==5 and chair.widget.Slider.maximum==30)
        assert(chair.widget.Slider.step==1 and chair.widget.Slider.MouseUsesStep==true)
        chair.widget.Slider:drag(24.49);click("apply");tick()
        assert(saved.cabin_chair_marker.size==24 and chair.widget.Slider:GetValue()==24)
        assert(chair.widget.SliderAmount.text=="24" and #requests==2)
        chair.widget.Slider:mouse(24.75);click("apply");tick()
        assert(saved.cabin_chair_marker.size==25 and #requests==3)
        for _,bound in ipairs({5,30}) do
            chair.widget.Slider:drag(bound);click("apply");tick()
            assert(saved.cabin_chair_marker.size==bound)
        end
        ''')

    def test_percent_steps_quantize_native_value_and_save_whole_percent(self):
        self.vm.execute(r'''
        select_mod("cabin_short_events")
        local balloon=number_row("balloon_factor")
        assert(balloon.widget.Slider.step==float32(0.01) and balloon.widget.Slider.MouseUsesStep==true)
        balloon.widget.Slider:drag(0.406);panel:stageNumbers()
        assert(panel.model.drafts.cabin_short_events.values.balloon_factor==0.41)
        assert(balloon.widget.Slider:GetValue()==float32(0.41) and balloon.last_read==float32(0.41))
        assert(balloon.widget.SliderAmount.text=="41 %")
        local sets=balloon.widget.Slider.sets
        panel:stageNumbers();click("apply");tick();click("apply")
        assert(balloon.widget.Slider.sets==sets and #requests==1,"snapped float32 caused repeated edit/save")
        assert(saved.cabin_short_events.balloon_factor==0.41 and saved.cabin_short_events.train_factor==2/3)
        balloon.widget.Slider:mouse(0.574);click("apply");tick()
        assert(saved.cabin_short_events.balloon_factor==0.57 and balloon.widget.SliderAmount.text=="57 %")
        balloon.widget.Slider:drag(1);click("apply");tick()
        assert(saved.cabin_short_events.balloon_factor==1 and balloon.widget.SliderAmount.text=="100 %")
        ''')

    def test_fraction_preserved_while_untouched_or_pending_then_quantized_on_movement(self):
        self.vm.execute(r'''
        select_mod("cabin_short_events")
        local balloon=number_row("balloon_factor")
        panel.model:edit("cabin_fast_turns","speed",3);click("apply")
        assert(panel.model.pending and #requests==1)
        panel:stageNumbers()
        assert(panel.model.drafts.cabin_short_events.values.balloon_factor==2/3 and balloon.widget.Slider.sets==1)
        tick();panel:stageNumbers();click("apply")
        assert(#requests==1 and not panel.model.drafts.cabin_short_events.dirty)
        assert(balloon.widget.SliderAmount.text=="67 %")
        balloon.widget.Slider:drag(0.668);click("apply");tick()
        assert(#requests==2 and saved.cabin_short_events.balloon_factor==0.67)
        assert(saved.cabin_short_events.train_factor==2/3)
        ''')

    def test_existing_fractional_config_is_not_rounded_on_open(self):
        self.vm.execute(r'''
        saved.cabin_fast_turns.speed=2.4;panel.model:open();select_mod("cabin_fast_turns")
        local record=number_row("speed")
        panel:stageNumbers();tick();click("apply")
        assert(#requests==0 and panel.model.drafts.cabin_fast_turns.values.speed==2.4)
        assert(record.widget.SliderAmount.text=="2" and record.widget.Slider.sets==1)
        record.widget.Slider:drag(2.6);click("apply");tick()
        assert(saved.cabin_fast_turns.speed==3 and record.widget.Slider:GetValue()==3)
        ''')

    def test_quantized_setter_readback_failure_does_not_edit_or_save(self):
        self.vm.execute(r'''
        select_mod("cabin_short_events")
        local record=number_row("balloon_factor")
        record.widget.Slider.setter_error=0.02
        record.widget.Slider:drag(0.406)
        local ok,cause=pcall(function() panel:stageNumbers() end)
        assert(not ok and tostring(cause):find("slider step readback differs: balloon_factor",1,true),tostring(cause))
        assert(tostring(cause):find("observed=",1,true) and tostring(cause):find("required=",1,true))
        assert(not panel.model.drafts.cabin_short_events.dirty and #requests==0)
        assert(saved.cabin_short_events.balloon_factor==2/3)
        ''')


def run(evidence_dir=None):
    comparisons = definition_source_checks()
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SliderBehavior)
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    output = stream.getvalue()
    print(output, end="")
    if evidence_dir is not None:
        evidence_dir = Path(evidence_dir).resolve()
        allowed = [(WORKSPACE / "Workspace/evidence/nexus-drafts" / name).resolve() for name in ("manual-slider1", "native-slider-integers1")]
        if not any(evidence_dir.is_relative_to(path) for path in allowed):
            raise ValueError("slider evidence path is outside manual-slider1/native-slider-integers1")
        evidence_dir.mkdir(parents=True, exist_ok=True)
        sources = [SCRIPTS / name for name in ("settings_panel.lua", "cabin_panel.lua", "cabin_store.lua", "cabin_codec.lua")] + [FAST, SHORT, CHAIR]
        report = {
            "status": "passed" if result.wasSuccessful() else "failed",
            "tests_run": result.testsRun,
            "failures": [{"test": str(test), "cause": cause} for test, cause in result.failures],
            "errors": [{"test": str(test), "cause": cause} for test, cause in result.errors],
            "source_sha256": {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
            "definition_fixtures": comparisons,
            "ui_boundary": "native Slider method/property seams expose IEEE754 float32 readback and stepped mouse input; shipped settings_panel owns quantization and uses the real cabin_panel/validators; repository definition snapshots remain active without sibling repositories; physical Slate movement remains a live acceptance check",
            "game_acceptance": False,
        }
        (evidence_dir / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        (evidence_dir / "tests.log").write_text(output, encoding="utf-8")
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path)
    run(parser.parse_args().evidence_dir)
elif __name__ == "<run_path>":
    run()
