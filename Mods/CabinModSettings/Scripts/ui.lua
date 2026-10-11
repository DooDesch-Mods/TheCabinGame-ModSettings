local M={}
function M.valid(v) return v and v:IsValid() end
function M.load(path,kind)
    local object=StaticFindObject(path)
    if not M.valid(object) then
        assert(IsInGameThread(),"UI asset load outside game thread")
        local loader=StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
        assert(M.valid(loader),"UI asset loader unavailable")
        if kind=="class" then object=loader:LoadClassAsset_Blocking(loader:Conv_SoftClassPathToSoftClassRef(loader:MakeSoftClassPath(path)))
        else object=loader:LoadAsset_Blocking(loader:Conv_SoftObjPathToSoftObjRef(loader:MakeSoftObjectPath(path))) end
    end
    assert(M.valid(object),"UI asset unavailable: " .. path)
    return object
end
function M.child(class,name,parent)
    local found
    for _,value in ipairs(FindAllOf(class) or {}) do
        if M.valid(value) and value:GetFName():ToString()==name and M.valid(value:GetOuter()) and M.valid(value:GetOuter():GetOuter()) and value:GetOuter():GetOuter():GetAddress()==parent:GetAddress() then
            assert(not found,"duplicate widget child: " .. name);found=value
        end
    end
    return assert(found,"widget child missing: " .. name)
end
function M.native(class,outer)
    local object=StaticConstructObject(StaticFindObject("/Script/UMG." .. class),outer)
    assert(M.valid(object),"native UI construction failed: " .. class)
    return object
end
function M.create(class,context,pc)
    local widget=StaticFindObject("/Script/UMG.Default__WidgetBlueprintLibrary"):Create(context,M.load(class,"class"),pc)
    assert(M.valid(widget),"widget Create failed: " .. class)
    return widget
end
function M.text(widget,value)
    widget:SetText(FText(value))
    assert(widget:GetText():ToString()==value,"UI text readback differs")
end
function M.buttonLabel(button,value)
    local found=false
    local function visit(widget)
        if widget:IsA("/Script/UMG.TextBlock") then M.text(widget,value);found=true
        elseif widget:IsA("/Script/UMG.PanelWidget") then
            for index=0,widget:GetChildrenCount()-1 do visit(widget:GetChildAt(index)) end
        end
    end
    visit(button:GetContent())
    assert(found,"button label missing")
end
return M
