"""Exercise the settings protocol in genuinely separate Lua 5.4 VMs."""
from pathlib import Path
import json
import sys
import tempfile
import hashlib

ROOT = Path(__file__).resolve().parents[1]
from lupa.lua54 import LuaRuntime

SHARED = ROOT / 'Mods/CabinModSettings/Scripts'
OUT = ROOT / 'dist/checks/core'
OUT.mkdir(parents=True,exist_ok=True)
checks = []
bus = {}
class Transport:
    def GetSharedVariable(self,key): return bus.get(key)
    def SetSharedVariable(self,key,value):
        if value is None: bus.pop(key,None)
        else: bus[key] = value

def vm():
    runtime = LuaRuntime(unpack_returned_tuples=True)
    runtime.globals().transport = Transport()
    runtime.globals().base = SHARED.as_posix()
    runtime.execute('package.path=base.."/?.lua;"..package.path; logs={}; function log(level,cause) logs[#logs+1]={level=level,cause=cause} end')
    return runtime

def check(name,operation):
    operation()
    checks.append(name)

owner, menu = vm(), vm()
with tempfile.TemporaryDirectory(dir=OUT,prefix='store-') as folder:
    owner.globals().settings_path = (Path(folder) / 'settings.dat').as_posix()
    owner.execute('''
        codec=require("cabin_codec"); storage=require("cabin_store")
        fields={{key="enabled",label="Enabled",type="boolean",default=true},
                {key="speed",label="Speed",type="number",default=2,min=0.01,max=10}}
        config=storage.new(settings_path,fields,log)
        registry=require("cabin_registry").new(transport,log)
        registry:register({id="test_speed",name="Speed",fields=fields},
            {read=function() return config:read() end,
             apply=function(values,action) assert(action==""); return config:save(values) end})
    ''')
    menu.execute('''
        registry=require("cabin_registry").new(transport,log)
        now=1; panel=require("cabin_panel").new(registry,function() return now end)
        panel:open()
    ''')
    check('separate VMs discover registration',lambda: menu.execute('assert(#registry:list()==1 and panel.drafts.test_speed.values.speed==2)'))
    check('Defaults only stages values',lambda: menu.execute('panel:edit("test_speed","speed",3); panel:defaults("test_speed"); assert(panel.drafts.test_speed.values.speed==2)'))
    assert not Path(owner.globals().settings_path).exists()
    check('Cancel discards changes without writes',lambda: menu.execute('panel:edit("test_speed","speed",4); panel:cancel(); panel:open(); assert(panel.drafts.test_speed.values.speed==2)'))
    check('invalid values stay visible without dispatch',lambda: menu.execute('panel:edit("test_speed","speed",0); assert(not panel:apply("test_speed") and panel.error and not panel.pending)'))
    menu.execute('panel:edit("test_speed","speed",3); assert(panel:apply("test_speed"))')
    check('Apply awaits acknowledgement',lambda: menu.execute('assert(panel.pending and panel.drafts.test_speed.snapshot.revision==0)'))
    owner.execute('registry:poll()')
    check('acknowledged Apply changes persistent state',lambda: menu.execute('panel:poll(); assert(not panel.pending and not panel.error and panel.drafts.test_speed.snapshot.revision==1 and panel.drafts.test_speed.values.speed==3)'))
    check('restart reads saved values',lambda: owner.execute('reloaded=storage.new(settings_path,fields,log); assert(reloaded.values.speed==3 and reloaded.revision==1)'))
    menu.execute('panel:edit("test_speed","speed",4); assert(panel:apply("test_speed"))')
    owner.execute('originalOpen=io.open; io.open=function(path,mode) if mode=="wb" then return nil,"injected disk failure",13 end return originalOpen(path,mode) end; registry:poll(); io.open=originalOpen')
    check('failed save keeps last valid state and visible cause',lambda: menu.execute('panel:poll(); assert(panel.error:find("injected disk failure",1,true) and panel.drafts.test_speed.snapshot.revision==1)'))
    owner.execute('assert(config.values.speed==3 and storage.new(settings_path,fields,log).values.speed==3)')
    menu.execute('assert(panel:apply("test_speed"))')
    owner.execute('originalRename=os.rename; os.rename=function(a,b) if a:sub(-8)==".pending" then return nil,"injected commit failure" end return originalRename(a,b) end; registry:poll(); os.rename=originalRename')
    check('failed commit restores previous file',lambda: owner.execute('assert(config.values.speed==3 and storage.new(settings_path,fields,log).values.speed==3)'))
    menu.execute('panel:poll(); assert(panel.error:find("injected commit failure",1,true)); assert(panel:apply("test_speed"))')
    owner.execute('''
        originalOpen=io.open; originalRename=os.rename;rejectRead=false
        io.open=function(path,mode) if rejectRead and path==settings_path and mode=="rb" then rejectRead=false;return nil,"injected readback failure",13 end return originalOpen(path,mode) end
        os.rename=function(a,b) local ok,cause=originalRename(a,b);if ok and a:sub(-8)==".pending" then rejectRead=true end;return ok,cause end
        registry:poll();io.open=originalOpen;os.rename=originalRename
        assert(config.values.speed==3 and storage.new(settings_path,fields,log).values.speed==3)
    ''')
    check('failed final readback restores last valid persisted state',lambda: menu.execute('panel:poll();assert(panel.error:find("injected readback failure",1,true) and not panel.pending)'))
    menu.execute('assert(panel:apply("test_speed")); now=12; panel:poll()')
    check('timeout remains pending and prohibits save replay',lambda: menu.execute('assert(panel.pending and panel.error:find("unknown",1,true)); assert(not pcall(function() panel:apply("test_speed") end))'))
    owner.execute('registry:poll()')
    check('late acknowledgement resolves timeout',lambda: menu.execute('panel:poll(); assert(not panel.pending and not panel.error and panel.drafts.test_speed.values.speed==4)'))
    check('failed operations logged with causes',lambda: owner.execute('local count=0; for _,row in ipairs(logs) do if row.level=="error" then count=count+1 end end; assert(count==3)'))
    check('corrupt primary recovers prior valid backup',lambda: owner.execute('local f=assert(io.open(settings_path,"wb")); assert(f:write("corrupt")); assert(f:close()); recovered=storage.new(settings_path,fields,log); assert(recovered.values.speed==3 and recovered.recovery)'))
    check('recovered store can commit replacement',lambda: owner.execute('recovered:save({enabled=false,speed=5}); assert(storage.new(settings_path,fields,log).values.speed==5)'))

check('codec accepts Unicode and nested metadata',lambda: owner.execute('local data={label="Größe",fields={{default=true},{value=2/3}}}; local copy=codec.decode(codec.encode(data)); assert(copy.label==data.label and copy.fields[2].value==data.fields[2].value)'))
check('codec rejects truncation, duplicate keys and code',lambda: owner.execute('for _,bytes in ipairs({"t1:s1:ab", "t2:s1:ab1s1:ab0", "return os.execute()", "n3:nan"}) do assert(not pcall(codec.decode,bytes)) end'))
late = vm()
late.execute('registry=require("cabin_registry").new(transport,log); registry:register({id="late",name="Late",fields={}}, {read=function() return {},0 end, apply=function(v) return v,1 end})')
check('late registration is discovered without reload',lambda: menu.execute('assert(#registry:list()==2)'))
bus.clear()
action_owner, action_menu = vm(), vm()
with tempfile.TemporaryDirectory(dir=OUT,prefix='action-') as folder:
    action_owner.globals().action_path = (Path(folder)/'action.dat').as_posix()
    action_owner.globals().other_path = (Path(folder)/'other.dat').as_posix()
    action_owner.execute('''
        storage=require("cabin_store");registry=require("cabin_registry").new(transport,log)
        action_fields={{key="profile",label="Profile",type="choice",default="current",options={{value="current"},{value="performance"}}},{key="restore",label="Restore previous",type="action"}}
        other_fields={{key="n",label="Number",type="number",default=2,min=1}}
        action_store=storage.new(action_path,action_fields,log);action_store:save({profile="performance"})
        other_store=storage.new(other_path,other_fields,log);writes={action=0,other=0};fail_action=false
        registry:register({id="test_action",name="Action",fields=action_fields},{read=function() return action_store:read() end,
            apply=function(values,action)
                assert(action=="" or action=="restore");if action=="" then return action_store:save(values) end
                if fail_action then error("injected restore failure") end
                writes.action=writes.action+1;return action_store:save({profile="current"})
            end})
        registry:register({id="test_other",name="Other",fields=other_fields},{read=function() return other_store:read() end,
            apply=function(values,action) assert(action=="");writes.other=writes.other+1;return other_store:save(values) end})
    ''')
    action_menu.execute('registry=require("cabin_registry").new(transport,log);now=1;panel=require("cabin_panel").new(registry,function() return now end);panel:open();panel:edit("test_other","n",4);assert(panel:action("test_action","restore"))')
    check('action immediately dispatches only its mod and awaits acknowledgement',lambda: action_menu.execute('assert(panel.pending.id=="test_action" and panel.drafts.test_other.dirty and panel.drafts.test_other.values.n==4)'))
    check('pending action prevents duplicate dispatch',lambda: action_menu.execute('assert(not pcall(function() panel:action("test_action","restore") end))'))
    action_owner.execute('registry:poll();assert(writes.action==1 and writes.other==0 and action_store.values.profile=="current")')
    check('action acknowledgement updates snapshot and preserves other drafts',lambda: action_menu.execute('panel:poll();assert(not panel.pending and not panel.error and panel.drafts.test_action.values.profile=="current" and not panel.drafts.test_action.dirty and panel.drafts.test_other.dirty and panel.drafts.test_other.values.n==4)'))
    check('Defaults remains staged after immediate action',lambda: action_menu.execute('panel:defaults("test_other");assert(not panel.pending and panel.drafts.test_other.values.n==2 and panel.drafts.test_other.dirty)'))
    action_owner.execute('registry:poll();assert(writes.other==0)')
    check('unregistered action never dispatches',lambda: action_menu.execute('assert(not pcall(function() panel:action("test_action","unknown") end) and not panel.pending)'))
    check('invalid action values retain visible error without dispatch',lambda: action_menu.execute('panel:edit("test_action","profile","invalid");assert(not panel:action("test_action","restore") and panel.error:find("invalid",1,true) and not panel.pending)'))
    action_menu.execute('panel:edit("test_action","profile","current");panel:edit("test_other","n",6);assert(panel:action("test_action","restore"))')
    action_owner.execute('fail_action=true;registry:poll();assert(writes.action==1 and writes.other==0)')
    check('failed action acknowledgement stays visible and leaves other drafts unsent',lambda: action_menu.execute('panel:poll();assert(panel.error:find("injected restore failure",1,true) and not panel.pending and panel.drafts.test_action.dirty and panel.drafts.test_other.dirty and panel.drafts.test_other.values.n==6)'))
    action_owner.execute('fail_action=false')
    action_menu.execute('assert(panel:action("test_action","restore"));now=12;panel:poll()')
    check('action timeout keeps unknown result pending without replay',lambda: action_menu.execute('assert(panel.pending and panel.error:find("unknown",1,true));assert(not pcall(function() panel:action("test_action","restore") end))'))
    action_owner.execute('registry:poll()')
    check('late action acknowledgement resolves timeout',lambda: action_menu.execute('panel:poll();assert(not panel.pending and not panel.error and panel.drafts.test_other.values.n==6)'))
    action_menu.execute('assert(panel:action("test_action","restore"));panel:cancel();assert(not panel.visible and panel.pending and not panel.queue and not panel.drafts.test_other)')
    action_owner.execute('registry:poll();assert(writes.other==0)')
    check('Cancel retains in-flight action acknowledgement and discards unsent drafts',lambda: action_menu.execute('panel:poll();assert(not panel.pending and not panel.visible);panel:open();assert(panel.drafts.test_other.values.n==2)'))
    action_menu.execute('panel:edit("test_other","n",5);assert(panel:applyAll())')
    action_owner.execute('registry:poll();assert(writes.other==1 and other_store.values.n==5)')
    check('normal Apply still persists other modified values',lambda: action_menu.execute('panel:poll();assert(not panel.pending and not panel.error and panel.drafts.test_other.values.n==5)'))
    action_menu.execute('assert(panel:action("test_action","restore"))')
    action_owner.execute('fail_action=true;registry:poll()')
    action_menu.execute('panel:poll();assert(panel.error:find("injected restore failure",1,true));panel:edit("test_action","profile","performance");assert(panel.drafts.test_action.action=="" and panel:applyAll())')
    action_owner.execute('registry:poll();assert(action_store.values.profile=="performance")')
    check('editing after failed action sends ordinary Apply without stale Restore',lambda: action_menu.execute('panel:poll();assert(not panel.pending and not panel.error and panel.drafts.test_action.values.profile=="performance")'))
syntax = owner.eval('function(source,name) return assert(load(source,name,"t",{})) end')
sources = []
for path in sorted(SHARED.glob('*.lua')):
    syntax(path.read_text(encoding='utf-8'),path.name)
    sources.append({'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
receipt={'checks':checks,'count':len(checks),'separate_lua_states':3,'sources':sources,'game_acceptance':False}
(OUT / 'receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'confirmed':len(checks),'receipt':str(OUT/'receipt.json'),'game_acceptance':False}))
