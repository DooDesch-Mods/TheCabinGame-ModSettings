"""Exercise native control callbacks against the shipped panel and real draft model."""
from pathlib import Path
import unittest

from lupa.lua54 import LuaRuntime

SCRIPTS = Path(__file__).resolve().parents[1] / "Mods/CabinModSettings/Scripts"

FIXTURE = r'''
package.path=scripts.."/?.lua;"..package.path
local codec=require("cabin_codec")
local definition={id="alpha",name="Alpha",fields={{key="enabled",label="Enabled",type="boolean",default=true},{key="restore",label="Restore previous",type="action"}}}
local other={id="beta",name="Beta",fields={{key="enabled",label="Enabled",type="boolean",default=true}}}
requests,callbacks,observers,animations,created={},{},{},{},{}
local registry={}
function registry:list()
    return {{definition=codec.copy(definition),values={enabled=true},revision=1},{definition=codec.copy(other),values={enabled=true},revision=1}}
end
function registry:request(id,token,revision,values,action)
    requests[#requests+1]={id=id,token=token,revision=revision,values=codec.copy(values),action=action}
end
function registry:response() return nil end
local serial=0
local function widget(class)
    serial=serial+1
    local value={address=serial,class=class,valid=true,children={},visible=true,viewport=false,Font={native=true,Size=36}}
    function value:GetAddress() return self.address end
    function value:IsValid() return self.valid end
    function value:IsVisible() return self.visible end
    function value:IsInViewport() return self.viewport end
    function value:GetParent() return self.parent end
    function value:SetFont(font) self.Font=font;self.font_sets=(self.font_sets or 0)+1 end
    function value:SetAutoWrapText(value) self.wrap=value end
    function value:SetIsEnabled(enabled) self.enabled=enabled end
    function value:SetVisibility(visibility) self.visibility=visibility end
    function value:GetVisibility() return self.visibility end
    function value:SetKeyboardFocus() self.focused=true end
    function value:SetWidthOverride(width) self.width=width end
    function value:SetMinDesiredWidth(width) self.minimum_width=width end
    function value:SetIsChecked(checked) self.checked=checked end
    function value:RemoveFromParent() self.parent=nil;self.viewport=false end
    function value:ClearChildren() self.children={} end
    function value:AddToViewport() self.viewport=true end
    function value:SetContent(child) self.content=child;child.parent=self end
    function value:AddChild(child)
        self.children[#self.children+1]=child;child.parent=self
        local slot={}
        function slot:IsValid() return true end
        function slot:SetPadding(padding) self.padding=padding end
        function slot:SetHorizontalAlignment(alignment) self.alignment=alignment end
        function slot:SetSize(size) self.size=size end
        function slot:SetAnchors(anchors) self.anchors=anchors end
        function slot:SetOffsets(offsets) self.offsets=offsets end
        child.Slot=slot
        return slot
    end
    value.AddChildToVerticalBox=value.AddChild
    value.AddChildToHorizontalBox=value.AddChild
    value.AddChildToCanvas=value.AddChild
    function value:StopAnimation(animation) assert(animation==self.gameplayprogress);self.stopped=true end
    function value:QueuePlayAnimationForward(animation,speed,restore)
        assert(restore==false)
        animations[#animations+1]={widget=self,animation=animation,speed=speed,direction="forward"}
        if self.gameplay_progressbar then self.gameplay_progressbar.Percent=1 end
    end
    function value:QueuePlayAnimation(animation,start,loops,mode,speed,restore)
        assert(start==0 and loops==1 and mode==0)
        self:QueuePlayAnimationForward(animation,speed,restore)
    end
    function value:QueuePlayAnimationReverse(animation,speed,restore)
        assert(restore==false)
        animations[#animations+1]={widget=self,animation=animation,speed=speed,direction="reverse"}
        if self.gameplay_progressbar then self.gameplay_progressbar.Percent=0 end
    end
    return value
end
local ui={}
function ui.valid(value) return value and value:IsValid() end
function ui.text(value,text) value.text=text end
function ui.native(class) return widget(class) end
function ui.child(class,name,parent)
    local child=assert(parent.named[name],"fixture native child absent: "..name)
    assert(child.class==class)
    return child
end
function ui.buttonLabel(button,text,font)
    button.caption.text=text
    if font then button.caption:SetFont(font) end
end
function ui.create(path)
    local row=widget(path)
    row.named={};row.WidgetTree=widget("WidgetTree")
    if path:find("CabinSettingsPanel",1,true) then
        row.named.CanvasPanel_43=widget("CanvasPanel")
        row.named.Border_103=widget("Border")
        row.named.TextBlock_2=widget("TextBlock")
        for _,name in ipairs({"Apply_B","Cancel_B","DeleteSave_B"}) do
            row[name]=widget("Button");row[name].caption=widget("TextBlock")
        end
        row.ApplyProgress={name="ApplyProgress"};row.CancelProgress={name="CancelProgress"}
    elseif path:find("CabinSelectorRow",1,true) then
        row.Gameplay_B=widget("Button")
        row.named.TextBlock_41=widget("TextBlock")
        row.gameplayprogress={name="gameplayprogress"}
        row.gameplay_progressbar=widget("ProgressBar");row.gameplay_progressbar.Percent=1
        function row.gameplay_progressbar:SetPercent(percent) self.Percent=percent end
    elseif path:find("CabinActionRow",1,true) then
        row.ResetInputs_B=widget("Button");row.named.TextBlock_74=widget("TextBlock")
    elseif path:find("CabinDefaultsRow",1,true) then
        row.Apply_B=widget("Button");row.named.TextBlock_56=widget("TextBlock")
        row.ApplyProgress={name="ApplyProgress"}
    elseif path:find("CabinBoolRow",1,true) then
        row.SlotTitle_T=widget("TextBlock");row.CheckBox_129=widget("CheckBox")
    else error("unexpected fixture asset: "..path) end
    created[#created+1]=row
    return row
end
package.loaded.ui=ui
package.loaded.mod_info={list=function() return {{name="Alpha",version="1",support="https://support.example/alpha"},{name="Beta",version="1"}} end}
local library=widget("WidgetBlueprintLibrary")
function library:SetInputMode_UIOnlyEx() end
function library:SetInputMode_GameAndUIEx() end
function StaticFindObject(path)
    assert(path=="/Script/UMG.Default__WidgetBlueprintLibrary",path)
    return library
end
local mod={registry=registry}
function mod:bind(path,callback) assert(not callbacks[path],"duplicate hook");callbacks[path]=callback end
function mod:observe(name,callback) observers[name]=callback end
function mod:log() end
panel=assert(loadfile(scripts.."/settings_panel.lua"))().start(mod,scripts.."/")
root,pc=widget("Menu"),widget("PC")
function open(mode) panel:open(root,pc,mode) end
function tick() observers["settings acknowledgement"]() end
function hook(class,delegate,target)
    local path="/Game/CabinModSettings/"..class.."."..class.."_C:"..delegate
    assert(callbacks[path],"hook absent: "..path)({get=function() return target end})
end
function tab(index,event)
    local suffix=({press="4_OnButtonPressedEvent",hover="1_OnButtonHoverEvent",unhover="2_OnButtonHoverEvent"})[event]
    hook("CabinSelectorRow","BndEvt__CabinSelectorRow_Gameplay_B_K2Node_ComponentBoundEvent_"..suffix.."__DelegateSignature",panel.selectors[index])
end
function action()
    for _,record in pairs(panel.rows) do
        if record.role=="action" then
            hook("CabinActionRow","BndEvt__CabinActionRow_ResetInputs_B_K2Node_ComponentBoundEvent_0_OnButtonPressedEvent__DelegateSignature",record.widget)
            return record
        end
    end
    error("action row missing")
end
function footer(event)
    local delegate=({apply="Apply_B_K2Node_ComponentBoundEvent_13_OnButtonPressedEvent",cancel="Cancel_B_K2Node_ComponentBoundEvent_12_OnButtonPressedEvent",apply_hover="Apply_B_K2Node_ComponentBoundEvent_14_OnButtonHoverEvent",apply_unhover="Apply_B_K2Node_ComponentBoundEvent_15_OnButtonHoverEvent",cancel_hover="Cancel_B_K2Node_ComponentBoundEvent_16_OnButtonHoverEvent",cancel_unhover="Cancel_B_K2Node_ComponentBoundEvent_17_OnButtonHoverEvent"})[event]
    hook("CabinSettingsPanel","BndEvt__CabinSettingsPanel_"..delegate.."__DelegateSignature",panel.widget)
end
function defaults(event,target)
    local suffix=({press="13_OnButtonPressedEvent",hover="14_OnButtonHoverEvent",unhover="15_OnButtonHoverEvent"})[event]
    hook("CabinDefaultsRow","BndEvt__CabinDefaultsRow_Apply_B_K2Node_ComponentBoundEvent_"..suffix.."__DelegateSignature",target or assert(panel.defaults))
end
'''


class NativeControls(unittest.TestCase):
    def setUp(self):
        self.vm = LuaRuntime(unpack_returned_tuples=True)
        self.vm.globals().scripts = SCRIPTS.as_posix()
        self.vm.execute(FIXTURE)

    def test_native_assets_caption_fonts_and_left_aligned_button_bounds(self):
        self.vm.execute(r'''
        open("settings")
        assert(panel.font_source:GetParent() and panel.font_source:GetVisibility()==1)
        assert(panel.font==panel.font_source.Font and panel.font.Size==20)
        for _,row in ipairs(panel.selectors) do
            assert(row.class:find("CabinSelectorRow",1,true))
            assert(row.Slot.alignment==1,"selector stretched over the row")
            assert(row.named.TextBlock_41.font_sets==nil,"original tab font replaced")
            assert(row.Gameplay_B and not row.LeftArrow_B,"arrow substitute retained")
        end
        local record=action()
        assert(record.widget.ResetInputs_B and record.widget.Slot.alignment==1)
        assert(record.widget.named.TextBlock_74.text=="Restore previous")
        assert(record.widget.named.TextBlock_74.font_sets==nil,"original Reset font replaced")
        assert(panel.widget.Apply_B.caption.font_sets==nil and panel.widget.Cancel_B.caption.font_sets==nil)
        ''')

    def test_selected_and_hover_underlines_and_deferred_selection(self):
        self.vm.execute(r'''
        open("settings")
        local first,second=panel.selectors[1],panel.selectors[2]
        assert(first.gameplay_progressbar.Percent==1 and second.gameplay_progressbar.Percent==0)
        tab(1,"hover");tab(1,"unhover")
        assert(#animations==0 and first.gameplay_progressbar.Percent==1,"active tab animated out")
        tab(2,"hover");assert(animations[1].direction=="forward" and animations[1].speed==3)
        tab(2,"unhover");assert(animations[2].direction=="reverse" and second.gameplay_progressbar.Percent==0)
        tab(2,"press");assert(panel.selected=="alpha" and panel.selection_requested.id=="beta")
        tick();assert(panel.selected=="beta")
        assert(first.gameplay_progressbar.Percent==0 and second.gameplay_progressbar.Percent==1)
        assert(#requests==0)
        ''')

    def test_restore_only_stages_owned_mod_action_and_apply_dispatches_it(self):
        self.vm.execute(r'''
        open("settings");action()
        assert(panel.model.drafts.alpha.action=="restore" and panel.model.drafts.alpha.dirty)
        assert(#requests==0)
        footer("apply")
        assert(#requests==1 and requests[1].id=="alpha" and requests[1].action=="restore")
        tab(2,"press");assert(panel.selection_requested==nil,"pending panel accepted selection")
        ''')

    def test_info_tabs_have_owned_selection_and_support_action_bounds(self):
        self.vm.execute(r'''
        open("info")
        assert(panel.info_selected=="Alpha" and panel.selectors[1].gameplay_progressbar.Percent==1)
        tab(1,"unhover");assert(#animations==0)
        for _,record in pairs(panel.rows) do
            if record.role=="support" then assert(record.widget.ResetInputs_B and record.widget.Slot.alignment==1) end
        end
        tab(2,"press");tick()
        assert(panel.info_selected=="Beta" and panel.selectors[2].gameplay_progressbar.Percent==1)
        assert(panel.selectors[1].gameplay_progressbar.Percent==0 and #requests==0)
        ''')

    def test_native_footer_animation_and_stale_foreign_callback_guards(self):
        self.vm.execute(r'''
        open("settings")
        footer("apply_hover");footer("apply_unhover");footer("cancel_hover");footer("cancel_unhover")
        assert(#animations==4)
        assert(animations[1].animation==panel.widget.ApplyProgress and animations[1].speed==2)
        assert(animations[2].speed==2.5 and animations[2].direction=="reverse")
        assert(animations[3].animation==panel.widget.CancelProgress)
        local foreign={GetAddress=function() return 999999 end}
        hook("CabinSelectorRow","BndEvt__CabinSelectorRow_Gameplay_B_K2Node_ComponentBoundEvent_1_OnButtonHoverEvent__DelegateSignature",foreign)
        assert(#animations==4 and panel.selection_requested==nil)
        panel.widget.viewport=false;tab(2,"hover");tab(2,"press");action()
        assert(#animations==4 and panel.selection_requested==nil and not panel.model.drafts.alpha.dirty)
        ''')

    def test_defaults_uses_native_apply_asset_at_right_footer(self):
        self.vm.execute(r'''
        open("settings")
        local row=assert(panel.defaults)
        assert(row.class:find("CabinDefaultsRow",1,true) and row.Apply_B and not row.ResetInputs_B)
        assert(row.named.TextBlock_56.text=="Defaults" and row.named.TextBlock_56.font_sets==nil)
        local footer=row:GetParent()
        assert(footer.class=="HorizontalBox" and #footer.children==4)
        assert(footer.children[1]==panel.widget.Apply_B and footer.children[2]==panel.widget.Cancel_B)
        assert(footer.children[3].class=="Spacer" and footer.children[3].Slot.size.SizeRule==1)
        assert(footer.children[4]==row and row.Slot.size.SizeRule==0 and row.Slot.padding.Right==0)
        assert(panel.widget.DeleteSave_B:GetParent()==nil,"old gray Defaults button still attached")
        defaults("hover");defaults("unhover")
        assert(#animations==2 and animations[1].animation==row.ApplyProgress and animations[1].speed==2)
        assert(animations[2].animation==row.ApplyProgress and animations[2].speed==2.5 and animations[2].direction=="reverse")
        ''')

    def test_defaults_cancel_and_apply_keep_draft_only_semantics(self):
        self.vm.execute(r'''
        open("settings")
        panel.model:edit("alpha","enabled",false);action()
        panel.model:edit("beta","enabled",false)
        defaults("press")
        assert(panel.model.drafts.alpha.values.enabled==true and panel.model.drafts.alpha.action=="")
        assert(panel.model.drafts.beta.values.enabled==false,"Defaults reset an unselected mod")
        assert(panel.selection_requested.id=="alpha" and #requests==0,"Defaults saved before Apply")
        tick();assert(panel.model.drafts.alpha.dirty)
        local old=panel.defaults
        footer("cancel")
        assert(#requests==0 and not panel.model.visible and panel.defaults==nil)
        open("settings")
        assert(panel.model.drafts.alpha.values.enabled==true and not panel.model.drafts.alpha.dirty)
        defaults("press",old)
        assert(not panel.model.drafts.alpha.dirty,"stale Defaults row changed a reopened panel")
        panel.model:edit("alpha","enabled",false)
        defaults("press");tick();footer("apply")
        assert(#requests==1 and requests[1].id=="alpha" and requests[1].values.enabled==true and requests[1].action=="")
        assert(panel.defaults.Apply_B.enabled==false,"pending Apply left Defaults enabled")
        defaults("press");assert(#requests==1 and panel.selection_requested==nil)
        ''')

    def test_defaults_legacy_delegate_and_info_stale_guard(self):
        self.vm.execute(r'''
        open("settings")
        panel.model:edit("alpha","enabled",false)
        hook("CabinSettingsPanel","BndEvt__CabinSettingsPanel_Apply_B_1_K2Node_ComponentBoundEvent_3_OnButtonPressedEvent__DelegateSignature",panel.widget)
        assert(panel.model.drafts.alpha.values.enabled==true and #requests==0)
        local old=panel.defaults
        footer("cancel");open("info")
        assert(panel.defaults==nil,"Info created a Defaults control")
        defaults("press",old);defaults("hover",old)
        assert(#requests==0 and #animations==0)
        ''')


def run():
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NativeControls))
    if not result.wasSuccessful():
        raise SystemExit(1)


if __name__ in ("__main__", "<run_path>"):
    run()
