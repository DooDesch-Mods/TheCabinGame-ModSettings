"""Exercise actual UI registrations and tick work with the panel closed/open."""
from pathlib import Path
from lupa.lua54 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
vm = LuaRuntime(unpack_returned_tuples=True)
vm.globals().directory = Path(globals().get('scripts_under_test', ROOT / 'Mods/CabinModSettings/Scripts')).as_posix()
vm.execute(r'''
package.path=directory..'/?.lua;'..package.path
print=function() end
package.preload.cabin_store=function() return {new=function() return {} end} end
package.preload.cabin_registry=function()
    return {new=function() return {poll=function() end} end}
end
package.preload.cabin_panel=function()
    return {new=function() return {poll=function() end} end}
end
package.preload.ui=function() return {valid=function(o) return o and o:IsValid() end} end
os.getenv=function() return nil end
local seconds=0
os.time=function() return seconds end
IsInGameThread=function() return true end
LoopInGameThreadWithDelay=function(_,callback) tick=callback;return 1 end
IsValidDelayedActionHandle=function() return true end
local lookups,scans,registrations=0,0,0
local available=false
StaticFindObject=function()
    lookups=lookups+1
    return {IsValid=function() return available end}
end
FindAllOf=function(name) assert(name=='Menu_WBP_C');scans=scans+1;return {} end
RegisterHook=function() registrations=registrations+1;return 1,2 end
local runtime=require('cabin_runtime')
local mod=runtime.start(directory,{name='Idle fixture',register=false,fields={}})
local panel=require('menu').start(mod,directory)
for i=1,100 do seconds=math.floor((i-1)/10);tick() end
assert(lookups==0,'closed UI must not search for optional functions: '..lookups)
assert(scans==10,'absent menu must scan at most once per second: '..scans)
assert(registrations==0)
panel.widget={IsValid=function() return true end,IsInViewport=function() return true end}
tick()
assert(lookups>0 and registrations==0,'open panel must keep unresolved hooks pending')
available=true;tick()
assert(registrations>10,'opening the panel must bind its actual control hooks')
local bound=registrations
local checked=lookups
for i=1,30 do tick() end
assert(registrations==bound and lookups==checked,'bound hooks must not be searched again')
panel.widget=nil
for i=1,30 do tick() end
assert(lookups==checked,'closing the panel must leave no optional hook search')
local messages={}
mod.log=function(_,level,message) messages[#messages+1]=level..': '..message end
RegisterHook=function() error('fixture registration failure') end
mod:bind('/Script/Test:Failure',function() end)
tick()
assert(mod.hooks['/Script/Test:Failure'].failed)
assert(messages[#messages]:find('fixture registration failure',1,true))
checked=lookups;tick();assert(lookups==checked,'failed binding must not repeat every tick')
''')
print('info: closed panel: zero function searches over 100 ticks; 10 menu scans; open/retry/close/failure checks passed')
