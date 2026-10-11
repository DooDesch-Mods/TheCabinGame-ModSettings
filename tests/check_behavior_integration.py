"""Check the new integration boundaries without claiming a game run."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SHARED=ROOT/'Mods/CabinModSettings/Scripts'
OUT=ROOT/'dist/checks/integration';OUT.mkdir(parents=True,exist_ok=True)
from lupa.lua54 import LuaRuntime
bus={};checks=[]
class Transport:
    def GetSharedVariable(self,key):return bus.get(key)
    def SetSharedVariable(self,key,value):
        if value is None:bus.pop(key,None)
        else:bus[key]=value
def vm():
    value=LuaRuntime(unpack_returned_tuples=True)
    value.globals().base=SHARED.as_posix();value.globals().ModRef=Transport()
    value.execute('package.path=base.."/?.lua;"..package.path;logs={};function log(level,cause) logs[#logs+1]={level=level,cause=cause} end')
    return value
def passed(name):checks.append(name)

# Model UObject identities and slot methods; these checks cover layout arithmetic,
# ordering and load order, not UE4SS conversions or the rendered menu.
layout=vm()
layout.execute('''
    function widget(address)
        local v={address=address,Slot={Size={Value=1,SizeRule=1},Padding={Left=4,Top=3,Right=4,Bottom=3},HorizontalAlignment=2,VerticalAlignment=2}}
        function v:GetAddress() return self.address end;function v:IsValid() return true end
        return v
    end
    function row(root)
        local r={children={root.MenuCardPlay_WBP,root.MenuCardProfile_WBP,root.MenuCardSocial_WBP},Slot={layout={Offsets={Left=-300,Top=2,Right=600,Bottom=90}}}}
        function r:GetChildrenCount() return #self.children end;function r:GetChildAt(i) return self.children[i+1] end
        function r:ClearChildren() self.children={} end
        function r.Slot:GetLayout() return self.layout end;function r.Slot:SetOffsets(o) self.layout.Offsets=o end
        function r:AddChildToHorizontalBox(w)
            self.children[#self.children+1]=w
            local s={};function s:IsValid() return true end
            function s:SetSize(v) self.Size=v end;function s:SetPadding(v) self.Padding=v end
            function s:SetHorizontalAlignment(v) self.HorizontalAlignment=v end;function s:SetVerticalAlignment(v) self.VerticalAlignment=v end
            w.Slot=s;return s
        end
        return r
    end
    function root(address) local r=widget(address);r.MenuCardPlay_WBP=widget(address+1);r.MenuCardProfile_WBP=widget(address+2);r.MenuCardSocial_WBP=widget(address+3);return r end
    helper=require("cabin_menu_layout")
    for _,reverse in ipairs({false,true}) do
        local address=reverse and 100 or 10;local r=root(address);local box=row(r);local left,right=widget(address+4),widget(address+5)
        if reverse then helper.attach(r,box,"settings",right,"right");helper.attach(r,box,"rejoin",left,"left")
        else helper.attach(r,box,"rejoin",left,"left");helper.attach(r,box,"settings",right,"right") end
        assert(box:GetChildrenCount()==5 and box:GetChildAt(0)==left and box:GetChildAt(4)==right)
        assert(box:GetChildAt(1)==r.MenuCardPlay_WBP and box:GetChildAt(2)==r.MenuCardProfile_WBP and box:GetChildAt(3)==r.MenuCardSocial_WBP)
        assert(box.Slot.layout.Offsets.Left==-500 and box.Slot.layout.Offsets.Right==1000)
        helper.attach(r,box,"settings",right,"right");assert(box:GetChildrenCount()==5)
    end
''')
passed('both menu-card load orders preserve identities, order, widths and repeated attachment')

bus.clear();owner,menu=vm(),vm()
owner.execute('''
    registry=require("cabin_registry").new(ModRef,log);writes={a=0,b=0}
    fields={{key="n",type="number",label="Number",default=2,min=1}}
    for _,name in ipairs({"a","b"}) do
        local id=name;local value={n=2};local revision=0
        registry:register({id=id,name=id,fields=fields},{read=function() return value,revision end,apply=function(v) value=v;revision=revision+1;writes[id]=writes[id]+1;return value,revision end})
    end
''')
menu.execute('registry=require("cabin_registry").new(ModRef,log);now=1;panel=require("cabin_panel").new(registry,function() return now end);panel:open();panel:edit("a","n",3);panel:edit("b","n",0);assert(not panel:applyAll() and not panel.pending)')
owner.execute('registry:poll();assert(writes.a==0 and writes.b==0)')
passed('Apply validates all modified views before the first write')
menu.execute('panel:edit("b","n",4);assert(panel:applyAll() and panel.pending.id=="a")')
owner.execute('registry:poll();assert(writes.a==1 and writes.b==0)')
menu.execute('panel:poll();assert(panel.pending.id=="b")')
owner.execute('registry:poll();assert(writes.a==1 and writes.b==1)')
menu.execute('panel:poll();assert(not panel.pending and not panel.error)')
passed('Apply dispatches each mod once and waits for individual acknowledgements')
menu.execute('panel:edit("a","n",5);panel:edit("b","n",6);assert(panel:applyAll());panel:cancel();assert(not panel.visible and not panel.queue and panel.pending)')
owner.execute('registry:poll();assert(writes.a==2 and writes.b==1)')
menu.execute('panel:poll();assert(not panel.pending);panel:open();assert(panel.drafts.a.values.n==5 and panel.drafts.b.values.n==4)')
passed('Cancel retains an already dispatched save acknowledgement and discards unsent drafts')

# The file bridge uses separate client and authority Lua states and real files.
bus.clear();publisher,authority=vm(),vm()
with tempfile.TemporaryDirectory(dir=OUT,prefix='bridge-') as folder:
    folder=Path(folder)
    for value in [publisher,authority]:
        value.globals().directory=folder.as_posix()
        value.execute('function IterateGameDirectories() return {Game={Binaries={Win64={__absolute_path=directory}}}} end')
    requested='76561198000000000'
    request_path=folder/'rejoin-request.dat';request_path.write_text('schema=1\nowner_id='+requested+'\n')
    publisher.execute('''
        registry=require("cabin_registry").new(ModRef,log)
        definition={id="cabin_fast_turns",name="Fast",fields={{key="enabled",label="Enabled",type="boolean",default=true},{key="speed",label="Speed",type="number",default=2,positive=true}}}
        registry:register(definition,{read=function() return {enabled=true,speed=3},1 end,apply=function() error("publisher must not apply") end})
        bridge=require("cabin_host_settings");request=bridge.publish("76561198000000000",log)
        local acknowledged,cause=bridge.acknowledged(request,"owned-authority-1");assert(not acknowledged and cause:find("absent",1,true))
    ''')
    authority.globals().request_path=request_path.as_posix()
    authority.execute('''
        originalGetenv=os.getenv;os.getenv=function(key) if key=="CABIN_REJOIN_PROCESS_ID" then return "owned-authority-1" elseif key=="CABIN_REJOIN_HOST_REQUEST_PATH" then return request_path end return originalGetenv(key) end
        mod={definition={id="cabin_fast_turns",fields={{key="enabled",label="Enabled",type="boolean",default=true},{key="speed",label="Speed",type="number",default=2,positive=true}}}}
        mod.store=require("cabin_store").new(directory.."/authority_settings.dat",mod.definition.fields,log)
        function mod:observe(name,callback) self.callback=callback end;function mod:log(level,cause) log(level,cause) end
        require("cabin_host_settings").start(mod);mod.callback();assert(mod.store.values.speed==3 and mod.store.revision==1);mod.callback();assert(mod.store.revision==1)
    ''')
    publisher.execute('assert(bridge.acknowledged(request,"owned-authority-1"));assert(not bridge.acknowledged(request,"wrong-authority"))')
    passed('authority persists host values once and acknowledges exact owner, token, process identity and values')
    publisher.execute('nextRequest=bridge.publish("76561198000000000",log);assert(nextRequest.token~=request.token and not bridge.acknowledged(nextRequest,"owned-authority-1"))')
    request_path.write_text('schema=1\nowner_id=76561198000000001\n')
    authority.execute('local ok,cause=pcall(mod.callback);assert(not ok and cause:find("owner differs",1,true));assert(mod.store.revision==1)')
    passed('new request rejects stale acknowledgements and mismatched original Rejoin owners')

receipt={'checks':checks,'count':len(checks),'separate_lua_states':5,'game_acceptance':False,
         'sources':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(SHARED.glob('*.lua'))]}
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'confirmed':len(checks),'game_acceptance':False,'receipt':str(OUT/'receipt.json')}))
