"""Check installed discovery, metadata isolation and safe filesystem paths."""
from pathlib import Path
from lupa.lua54 import LuaRuntime

root = Path(__file__).resolve().parents[1]
vm = LuaRuntime(unpack_returned_tuples=True)
vm.globals().scripts = (root / "Mods/CabinModSettings/Scripts").as_posix()
vm.execute(r'''
package.path=scripts .. "/?.lua;" .. package.path
local info=require("mod_info")
local function metadata(version,support) return "version="..version.."\nsupport="..support.."\n" end
local parsed=info.metadata(metadata("0.1.0","https://support.doodesch.de/modsettings"))
assert(parsed.version=="0.1.0" and parsed.support=="https://support.doodesch.de/modsettings")
for _,bytes in ipairs({
    "", "version=0.1.0\n", "version=0.1.0\nversion=0.2.0\nsupport=https://example.com\n",
    metadata("1\0injected","https://example.com"),
    metadata("1","file:///C:/Windows"), metadata("1","http://example.com"),
    metadata("1","https://example.com@evil.test"), metadata("1","https://example.com/../foreign"),
    metadata("1","https://."), metadata("1","https://-"), metadata("1","https://foo..bar"),
    metadata("1","https://-foo.test"), metadata("1","https://foo-.test"),
    metadata("1","https://example.com/"..string.rep("a",257)), string.rep("a",8193),
}) do assert(not pcall(info.metadata,bytes),"malformed metadata accepted") end
local files={
    ["C:/owned/Mods/mods.txt"]="Alpha : 1\nStale : 1\n../foreign : 1\nBeta : 0\nNative Mod : 1\n",
    ["C:/owned/Mods/Alpha/Scripts/main.lua"]=string.rep("a",20000),
    ["C:/owned/Mods/Beta/Scripts/main.lua"]="return 1",
    ["C:/owned/Mods/Alpha/mod-info.ini"]=metadata("1.2.3","https://example.com/alpha"),
    ["C:/owned/Mods/Native Mod/dlls/main.dll"]="native",
    ["C:/owned/Mods/Native Mod/mod-info.ini"]=metadata("2.0","https://example.com/native"),
    ["C:/owned/Mods/Directory Only/Scripts/main.lua"]="return 1",
    ["C:/foreign/Mods/Foreign/Scripts/main.lua"]="return 1",
}
local failures,opened={},{}
io.open=function(path)
    opened[#opened+1]=path
    local failure=failures[path]
    if failure and failure.open then return nil,failure.open,13 end
    local bytes=files[path]
    if not bytes then return nil,"not found",2 end
    return {
        read=function(_,limit)
            if failure and failure.read then return nil,failure.read end
            if #bytes==0 then return nil end
            return bytes:sub(1,limit)
        end,
        close=function()
            if failure and failure.close then return nil,failure.close end
            return true
        end,
    }
end
local logs={}
local function log(level,message) logs[#logs+1]=level..":"..message end
local registry={list=function() return {
    {definition={name="CabinModSettings"}}, {definition={name="Display label without a folder"}},
    {definition={name="Stale"}}, {definition={name="../foreign"}},
    {definition={name="C:\\foreign"}}, {definition={name="."}}, {definition={name=".."}},
} end}
local function list() logs={};return info.list("C:/owned/Mods/CabinModSettings/Scripts/",registry,log) end
function IterateGameDirectories() return {} end
local function by_name(rows)
    local result={};for _,row in ipairs(rows) do result[row.name]=row end;return result
end
local rows=list()
assert(#rows==4 and rows[1].name=="Alpha" and rows[1].version=="1.2.3")
assert(rows[2].name=="Beta" and rows[2].version==nil and rows[2].support==nil)
assert(rows[3].name=="CabinModSettings" and rows[4].name=="Native Mod")
assert(rows[4].version=="2.0" and rows[4].support=="https://example.com/native")
assert(#logs==1 and logs[1]:find("2 installed mods",1,true))
for _,path in ipairs(opened) do
    assert(not path:find("../",1,true) and not path:find("/C:",1,true),"unsafe path was opened")
end

local mods={__absolute_path="C:\\owned\\Mods\\"}
mods.directory={__name="Directory Only",__absolute_path="C:/owned/Mods/Directory Only/"}
mods.escape={__name="../foreign",__absolute_path="C:/foreign"}
mods.wrong={__name="Foreign",__absolute_path="C:/foreign/Mods/Foreign"}
mods.fake={__name="Fake",__absolute_path="C:/owned/Mods/Fake"}
local tree={Owned={Mods=mods},Foreign={Mods={__absolute_path="C:/foreign/Mods"}}}
tree.cycle=tree
function IterateGameDirectories() return tree end
rows=list()
assert(#rows==5 and by_name(rows)["Directory Only"] and not by_name(rows).Foreign)
registry.list=function() return {{definition={name="Alpha"}},{definition={name="alpha"}}} end
files["C:/owned/Mods/alpha/Scripts/main.lua"]=files["C:/owned/Mods/Alpha/Scripts/main.lua"]
mods.alpha={__name="Alpha",__absolute_path="C:/owned/Mods/Alpha"}
rows=list();assert(#rows==5 and by_name(rows).Alpha and not by_name(rows).alpha)

for _,failure in ipairs({
    {bytes="",cause="requires version and support"},
    {bytes=metadata("1","https://-"),cause="host is invalid"},
    {bytes=string.rep("a",8193),cause="exceeds 8192 bytes"},
    {open="injected permission denial",cause="injected permission denial"},
    {read="injected read failure",cause="injected read failure"},
    {close="injected close failure",cause="injected close failure"},
}) do
    local path="C:/owned/Mods/Alpha/mod-info.ini"
    files[path]=failure.bytes or metadata("1","https://example.com")
    failures[path]=failure
    local result=by_name(list())
    assert(not result.Alpha.version and not result.Alpha.support)
    assert(result["Native Mod"].version=="2.0","bad metadata hid another installed mod")
    local found=false
    for _,entry in ipairs(logs) do
        if entry:find("warn:mod metadata Alpha:",1,true) and entry:find(failure.cause,1,true) then found=true end
    end
    assert(found,"metadata failure cause was hidden")
    failures[path]=nil
end
function IterateGameDirectories() error("injected enumeration failure") end
assert(#list()==4 and logs[1]:find("injected enumeration failure",1,true))
IterateGameDirectories=nil
assert(#list()==4 and logs[1]:find("IterateGameDirectories unavailable",1,true))
function IterateGameDirectories() return nil end
assert(#list()==4 and logs[1]:find("returned no directory table",1,true))
for _,directory in ipairs({"C:/owned/NotMods/CabinModSettings/Scripts/","C:/owned/Mods/../Scripts/"}) do
    assert(not pcall(info.list,directory,registry,log),"invalid Mods root accepted")
end
failures["C:/owned/Mods/mods.txt"]={read="injected config read failure"}
local ok,cause=pcall(list)
assert(not ok and cause:find("injected config read failure",1,true))
''')
print("info: metadata, Lua/native discovery, spaced folders, stale entries, exact root, cycles, unsafe paths and failure isolation passed")
