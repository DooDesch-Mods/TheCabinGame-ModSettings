local codec = require("cabin_codec")
local M = {}
local PREFIX = "CabinMenuLayoutV1."
local function valid(v) return v and v:IsValid() end
local function originals(root)
    return {root.MenuCardPlay_WBP,root.MenuCardProfile_WBP,root.MenuCardSocial_WBP}
end
function M.originals(root,row)
    local expected = originals(root)
    local previous = -1
    for _,widget in ipairs(expected) do
        assert(valid(widget),"original menu card missing")
        local found
        for index=0,row:GetChildrenCount()-1 do
            if row:GetChildAt(index):GetAddress()==widget:GetAddress() then assert(not found,"duplicate original card");found=index end
        end
        assert(found and found>previous,"original menu card order changed")
        previous=found
    end
    return expected
end
function M.attach(root,row,id,widget,side)
    assert(id=="rejoin" and side=="left" or id=="settings" and side=="right","unknown extra menu slot")
    local base=M.originals(root,row)
    local key=PREFIX .. root:GetAddress() .. "."
    local bytes=ModRef:GetSharedVariable(key .. "baseline")
    local baseline
    if bytes then baseline=codec.decode(bytes) else
        assert(row:GetChildrenCount()==3,"shared layout baseline requires three original cards")
        local layout=row.Slot:GetLayout()
        baseline={left=layout.Offsets.Left,top=layout.Offsets.Top,width=layout.Offsets.Right,height=layout.Offsets.Bottom,slots={}}
        for index,card in ipairs(base) do
            local slot=card.Slot
            baseline.slots[index]={size={Value=slot.Size.Value,SizeRule=slot.Size.SizeRule},padding={Left=slot.Padding.Left,Top=slot.Padding.Top,Right=slot.Padding.Right,Bottom=slot.Padding.Bottom},horizontal=slot.HorizontalAlignment,vertical=slot.VerticalAlignment}
        end
        ModRef:SetSharedVariable(key .. "baseline",codec.encode(baseline))
    end
    ModRef:SetSharedVariable(key .. id,widget)
    local left,right=ModRef:GetSharedVariable(key .. "rejoin"),ModRef:GetSharedVariable(key .. "settings")
    local cards={}
    if valid(left) then cards[#cards+1]=left end
    for _,card in ipairs(base) do cards[#cards+1]=card end
    if valid(right) then cards[#cards+1]=right end
    local expected={}
    for _,card in ipairs(cards) do expected[card:GetAddress()]=true end
    for index=0,row:GetChildrenCount()-1 do assert(expected[row:GetChildAt(index):GetAddress()],"unregistered extra menu card") end
    local width=baseline.width*#cards/3
    row.Slot:SetOffsets({Left=baseline.left-(width-baseline.width)/2,Top=baseline.top,Right=width,Bottom=baseline.height})
    row:ClearChildren()
    for index,card in ipairs(cards) do
        local originalIndex=1
        for i,v in ipairs(base) do if v:GetAddress()==card:GetAddress() then originalIndex=i end end
        local shape=baseline.slots[originalIndex]
        local slot=row:AddChildToHorizontalBox(card)
        assert(valid(slot),"menu card attachment failed")
        slot:SetSize(shape.size);slot:SetPadding(shape.padding)
        slot:SetHorizontalAlignment(shape.horizontal);slot:SetVerticalAlignment(shape.vertical)
        assert(row:GetChildAt(index-1):GetAddress()==card:GetAddress(),"menu row readback differs")
    end
    assert(row:GetChildrenCount()==#cards and math.abs(row.Slot:GetLayout().Offsets.Right-width)<0.001,"menu width/count readback differs")
    return #cards
end
return M
