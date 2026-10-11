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
syntax = owner.eval('function(source,name) return assert(load(source,name,"t",{})) end')
sources = []
for path in sorted(SHARED.glob('*.lua')):
    syntax(path.read_text(encoding='utf-8'),path.name)
    sources.append({'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
receipt={'checks':checks,'count':len(checks),'separate_lua_states':3,'sources':sources,'game_acceptance':False}
(OUT / 'receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'confirmed':len(checks),'receipt':str(OUT/'receipt.json'),'game_acceptance':False}))
