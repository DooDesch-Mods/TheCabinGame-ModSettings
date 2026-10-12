local M={}
local function name_valid(name)
    return type(name)=="string" and #name>0 and name~="." and name~=".."
        and not name:find('[%c/\\:<>"|?*]') and not name:find("[%. ]$")
end
local function present(path)
    local file,cause,code=io.open(path,"rb")
    if not file then
        assert(code==2,"check installed mod " .. path .. ": " .. tostring(cause))
        return false
    end
    local closed,cause=file:close()
    assert(closed,"close installed mod " .. path .. ": " .. tostring(cause))
    return true
end
local function read(path,limit)
    local file,cause,code=io.open(path,"rb")
    if not file then
        assert(code==2,"read " .. path .. ": " .. tostring(cause))
        return nil,cause
    end
    local bytes,readCause=file:read(limit+1)
    local closed,closeCause=file:close()
    assert(bytes or not readCause,"read " .. path .. ": " .. tostring(readCause))
    assert(closed,"close " .. path .. ": " .. tostring(closeCause))
    bytes=bytes or ""
    assert(#bytes<=limit,"file exceeds " .. tostring(limit) .. " bytes: " .. path)
    return bytes
end
function M.metadata(bytes)
    assert(type(bytes)=="string" and #bytes<=8192,"mod metadata exceeds 8 KiB or is not text")
    local values={}
    for line in (bytes .. "\n"):gmatch("([^\r\n]+)") do
        local key,value=line:match("^([a-z]+)=(.*)$")
        assert(key and (key=="version" or key=="support") and not values[key],"mod metadata has an unknown or duplicate field")
        assert(#value>0 and #value<=256,"mod metadata value is empty or too long")
        assert(not value:find("%c"),"mod metadata contains a control character")
        values[key]=value
    end
    assert(values.version and values.support,"mod metadata requires version and support")
    assert(values.support:match("^https://[%w%.%-]+/[%w/_%-]*$") or values.support:match("^https://[%w%.%-]+$"),"mod support URL requires HTTPS")
    local host=values.support:match("^https://([^/]+)")
    assert(not host:find("%.%.") and not host:find("^%.") and not host:find("%.$"),"mod support URL host is invalid")
    for label in host:gmatch("[^%.]+") do
        assert(#label<=63 and label:match("^[%w]") and label:match("[%w]$"),"mod support URL host is invalid")
    end
    return values
end
function M.list(directory,registry,log)
    local parent,mods,name=directory:gsub("\\","/"):match("^(.*)/([^/]+)/([^/]+)/Scripts/$")
    assert(parent and mods:lower()=="mods" and name_valid(name),"mod directory does not end in Mods/name/Scripts")
    local folder=parent .. "/" .. mods
    local function installed_mod(name)
        return name_valid(name) and (present(folder .. "/" .. name .. "/Scripts/main.lua")
            or present(folder .. "/" .. name .. "/dlls/main.dll"))
    end
    local installed={[name:lower()]=name}
    local function add(name) installed[name:lower()]=name end
    local config,configCause=read(folder .. "/mods.txt",65536)
    if config then
        for line in config:gmatch("[^\r\n]+") do
            local name=line:match("^%s*(.-)%s*:%s*[01]%s*$")
            if installed_mod(name) then add(name) end
        end
    else log("warn","mod list file " .. folder .. "/mods.txt unavailable: " .. tostring(configCause)) end
    for _,snapshot in ipairs(registry:list()) do
        local name=snapshot.definition.name
        if installed_mod(name) then add(name) end
    end
    if type(IterateGameDirectories)=="function" then
        local seen,stack={},{}
        local ok,tree=pcall(IterateGameDirectories)
        if not ok then log("warn","enumerate installed mods: " .. tostring(tree))
        elseif type(tree)~="table" then log("warn","enumerate installed mods returned no directory table")
        else stack[1]=tree end
        while #stack>0 do
            local node=table.remove(stack)
            if not seen[node] then
                seen[node]=true
                local absolute=node.__absolute_path
                if type(absolute)=="string" and absolute:gsub("\\","/"):gsub("/$",""):lower()==folder:lower() then
                    for _,child in pairs(node) do
                        if type(child)=="table" and name_valid(child.__name) and type(child.__absolute_path)=="string" then
                            local path=child.__absolute_path:gsub("\\","/"):gsub("/$","")
                            if path:lower()==(folder .. "/" .. child.__name):lower() and installed_mod(child.__name) then add(child.__name) end
                        end
                    end
                else
                    for key,child in pairs(node) do
                        if type(key)=="string" and key:sub(1,2)~="__" and type(child)=="table" then stack[#stack+1]=child end
                    end
                end
            end
        end
    else
        log("warn","enumerate installed mods: IterateGameDirectories unavailable")
    end
    local result,missing={},0
    for _,name in pairs(installed) do
        local ok,info=pcall(function()
            local bytes=read(folder .. "/" .. name .. "/mod-info.ini",8192)
            return bytes and M.metadata(bytes) or nil
        end)
        if not ok then log("warn","mod metadata " .. name .. ": " .. tostring(info));info=nil end
        if not info then missing=missing+1;info={} end
        result[#result+1]={name=name,version=info.version,support=info.support}
    end
    table.sort(result,function(a,b) return a.name:lower()<b.name:lower() end)
    if missing>0 then log("info",tostring(missing) .. " installed mods have no version/support metadata") end
    return result
end
return M
