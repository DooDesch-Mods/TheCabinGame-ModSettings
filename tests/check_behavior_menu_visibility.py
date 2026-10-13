"""Exercise the shipped menu observer against original card visibility transitions."""
from pathlib import Path
from lupa.lua54 import LuaRuntime

ROOT=Path(__file__).resolve().parents[1]
MODULE=ROOT/'Mods/CabinModSettings/Scripts/menu.lua'
FIXTURE=r'''
local modulepath=...
local serial=0
function object()
 serial=serial+1
 local value={address=serial,valid=true,visibility=0,opacity=1,hovered=false}
 function value:IsValid() return self.valid end
 function value:GetAddress() return self.address end
 function value:GetParent() return self.parent end
 function value:GetVisibility() return self.visibility end
 function value:SetVisibility(number) self.visibility=number;visibility_sets=visibility_sets+1 end
 function value:GetRenderOpacity() return self.opacity end
 function value:SetRenderOpacity(number) self.opacity=number;opacity_sets=opacity_sets+1 end
 function value:IsHovered() return self.hovered end
 return value
end
visibility_sets=0;opacity_sets=0;mesh_sets=0;captures=0;opens=0;creates=0
function actor()
 local a=object();a.Disabled=false;a.PlayFlip=false
 a.CardMesh=object();a.CardMesh.visible=true
 function a.CardMesh:IsVisible() return self.visible end
 function a.CardMesh:SetVisibility(visible,children)
  assert(children==true,'native child visibility must follow its card');mesh_sets=mesh_sets+1
  if not wrong_mesh_readback then self.visible=visible end
 end
 a.FlipStart_TL=object();a.FlipStart_TL.position=1
 function a.FlipStart_TL:GetPlaybackPosition() return self.position end
 a.SceneCaptureComponent2D=object()
 function a.SceneCaptureComponent2D:CaptureScene() captures=captures+1 end
 return a
end
parent=object();function parent:GetChildrenCount() return 3 end
root=object();root['3CardsHorizBox']=parent
function root:IsInViewport() return true end
reference=object();reference.parent=parent;reference.Social_Card=actor();root.MenuCardSocial_WBP=reference
root.MenuCardPlay_WBP=object();root.MenuCardPlay_WBP.Play_Card=actor()
root.MenuCardProfile_WBP=object();root.MenuCardProfile_WBP.Profile_Card=actor()
card=object();card.parent=parent;ownActor=actor();pc=object()
native_unhover=0;ownActor.Flip_TL=object()
function ownActor.Flip_TL:IsReversing() return self.reversing or false end
function card:Unhovered_E() native_unhover=native_unhover+1;ownActor.PlayFlip=false;ownActor.Flip_TL.reversing=true end
local panel={open=function(self,r,p,mode) assert(r==root and p==pc and mode=='settings');opens=opens+1 end}
package.loaded.ui={valid=function(value) return value and value:IsValid() end,create=function() creates=creates+1;error('unexpected native creation') end}
package.loaded.settings_panel={start=function() return panel end}
os.getenv=function() return nil end
mod={bind=function() end,log=function() end,observe=function(self,label,callback) observe=callback end}
function FindAllOf(name) assert(name=='Menu_WBP_C');return {root} end
module=assert(loadfile(modulepath))();module.start(mod,'fixture directory')
state={root=root,pc=pc,card=card,actor=ownActor,hovered=false}
function stateValue(value)
 for index=1,100 do
  local name=debug.getupvalue(observe,index)
  if not name then break end
  if name=='state' then debug.setupvalue(observe,index,value);return end
 end
 error('actual menu observer state upvalue missing')
end
stateValue(state)
function reject(expected)
 local ok,cause=pcall(observe)
 assert(not ok and tostring(cause):find(expected,1,true),tostring(cause))
end
'''

CASES={
    'native Host hide and original menu return':r'''
        observe();assert(mesh_sets==0 and captures==0)
        reference.Social_Card.CardMesh.visible=false;parent.visibility=3;observe()
        assert(not ownActor.CardMesh.visible and mesh_sets==1 and captures==1 and creates==0)
        observe();assert(mesh_sets==1 and captures==1)
        reference.Social_Card.CardMesh.visible=true;parent.visibility=4;observe()
        assert(ownActor.CardMesh.visible and mesh_sets==2 and captures==2)
    ''',
    'actual widget visibility and opacity are mirrored without dialog guesses':r'''
        reference.visibility=2;reference.opacity=0.25;observe()
        assert(card.visibility==2 and card.opacity==0.25 and visibility_sets==1 and opacity_sets==1)
        observe();assert(visibility_sets==1 and opacity_sets==1)
        reference.visibility=0;reference.opacity=1;observe()
        assert(card.visibility==0 and card.opacity==1)
    ''',
    'normal Settings callback remains available':r'''
        state.open_requested='settings';observe();assert(opens==1 and not state.open_requested)
        observe();assert(opens==1)
    ''',
    'native hover return remains available':r'''
        state.hovered=true;ownActor.PlayFlip=true;observe()
        assert(native_unhover==1 and not ownActor.PlayFlip and not state.return_front)
        observe();assert(native_unhover==1)
    ''',
    'foreign native parent fails before any setter':r'''
        card.parent=object();reference.opacity=0.25
        reject('visibility parent differs');assert(mesh_sets==0 and opacity_sets==0 and visibility_sets==0)
    ''',
    'invalid original state and failed native readback remain visible':r'''
        reference.opacity=0/0;reject('Social opacity invalid');reference.opacity=1
        reference.Social_Card.CardMesh.visible=false;wrong_mesh_readback=true
        reject('mesh visibility readback differs');assert(mesh_sets==1 and captures==0)
    ''',
    'original Social intro reveal gate remains unchanged':r'''
        stateValue(nil);reference.Social_Card.CardMesh.visible=false;observe();assert(creates==0)
        reference.Social_Card.CardMesh.visible=true;reference.Social_Card.FlipStart_TL.position=0.14
        observe();assert(creates==0 and mesh_sets==0)
    ''',
}

for name,code in CASES.items():
    vm=LuaRuntime(unpack_returned_tuples=True)
    vm.execute(FIXTURE,MODULE.as_posix())
    vm.execute(code)
    print('passed: '+name)
