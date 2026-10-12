local directory=assert(debug.getinfo(1,"S").source:match("^@(.+[/\\])"))
package.path=directory .. "?.lua;" .. package.path
local mod=require("cabin_runtime").start(directory,{id="cabin_mod_settings",name="CabinModSettings",fields={},register=false})
require("menu").start(mod,directory)
return mod
