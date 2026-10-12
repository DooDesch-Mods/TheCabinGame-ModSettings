local ui=require("ui")
local M={}
local PANEL="/Game/CabinModSettings/CabinSettingsPanel.CabinSettingsPanel_C"
local CHOICE="/Game/CabinModSettings/CabinChoiceRow.CabinChoiceRow_C"
local BOOL="/Game/CabinModSettings/CabinBoolRow.CabinBoolRow_C"
local NUMBER="/Game/CabinModSettings/CabinNumberRow.CabinNumberRow_C"
function M.start(mod,directory)
    local model=require("cabin_panel").new(mod.registry,os.time)
    local self={model=model,rows={},selectors={},rendering=false}
    local function label(text)
        local widget=ui.native("TextBlock",self.widget.WidgetTree)
        widget:SetFont(self.font);ui.text(widget,text)
        return widget
    end
    local function add(box,widget)
        local slot=box:AddChildToVerticalBox(widget)
        assert(ui.valid(slot),"settings row attachment failed")
        slot:SetPadding({Left=12,Top=8,Right=12,Bottom=8})
        return slot
    end
    local function buttonRow(text,role)
        local row=ui.create(CHOICE,self.root,self.pc)
        row.RightArrow_B:SetVisibility(1);row.OptionType_T:SetVisibility(1)
        local title=row.SlotTitle_T
        title:RemoveFromParent();row.LeftArrow_B:SetContent(title)
        title:SetFont(self.font);title:SetAutoWrapText(true)
        row.LeftArrow_B:SetRenderScale({X=1,Y=1})
        local box=row.LeftArrow_B:GetParent()
        box:ClearChildren()
        box:AddChildToHorizontalBox(row.LeftArrow_B):SetSize({Value=1,SizeRule=1})
        row.LeftArrow_B.Slot:SetPadding({Left=0,Top=0,Right=0,Bottom=0})
        title.Slot:SetPadding({Left=8,Top=6,Right=8,Bottom=6})
        title.Slot:SetHorizontalAlignment(1)
        local border=ui.child("Border","Invert_13",row)
        border:SetPadding({Left=0,Top=0,Right=0,Bottom=0})
        border.Slot:SetPadding({Left=0,Top=0,Right=0,Bottom=0})
        ui.child("VerticalBox","VerticalBox_45",row).Slot:SetPadding({Left=0,Top=0,Right=0,Bottom=0})
        for _,brush in ipairs({"Normal","Hovered","Pressed","Disabled"}) do row.LeftArrow_B.WidgetStyle[brush].DrawAs=0 end
        ui.text(title,text)
        self.rows[row:GetAddress()]={widget=row,role=role}
        return row
    end
    local function status()
        if ui.valid(self.error) then
            ui.text(self.error,model.error or (model.pending and "Applying settings" or ""))
            self.widget.Apply_B:SetIsEnabled(not model.pending)
            self.widget.DeleteSave_B:SetIsEnabled(not model.pending)
            self.content:SetIsEnabled(not model.pending)
            self.left:SetIsEnabled(not model.pending)
        end
    end
    function self:select(id)
        assert(model.drafts[id],"selected mod unavailable")
        self.selected=id;self.rendering=true
        self.content:ClearChildren()
        for address,record in pairs(self.rows) do if record.role~="select" then self.rows[address]=nil end end
        local draft=model.drafts[id]
        add(self.content,label(draft.snapshot.definition.name))
        for _,field in ipairs(draft.snapshot.definition.fields) do
            local title=field.label .. (field.host and " - Host setting (next round)" or "")
            local row
            if field.type=="boolean" then
                row=ui.create(BOOL,self.root,self.pc)
                ui.text(row.SlotTitle_T,title)
                self.rows[row:GetAddress()]={widget=row,id=id,field=field,role="boolean"}
                row.CheckBox_129:SetIsChecked(draft.values[field.key])
            elseif field.type=="number" then
                row=ui.create(NUMBER,self.root,self.pc)
                ui.text(row.SlotTitle_T,title)
                self.rows[row:GetAddress()]={widget=row,id=id,field=field,role="number"}
                local value=draft.values[field.key]
                row.CheckBox_129:SetText(FText(type(value)=="number" and string.format("%.17g",value) or tostring(value)))
            elseif field.type=="choice" then
                row=ui.create(CHOICE,self.root,self.pc)
                ui.text(row.SlotTitle_T,title)
                local index
                for i,option in ipairs(field.options) do if option.value==draft.values[field.key] then index=i end end
                assert(index,"choice value absent from metadata")
                ui.text(row.OptionType_T,field.options[index].label)
                self.rows[row:GetAddress()]={widget=row,id=id,field=field,role="choice",index=index}
            elseif field.type=="action" then
                row=buttonRow(title,"action")
                self.rows[row:GetAddress()].id=id;self.rows[row:GetAddress()].field=field
            else error("unsupported settings control: " .. tostring(field.type)) end
            add(self.content,row)
        end
        self.rendering=false;status()
        mod:log("info","settings view populated: " .. id .. "; visual acceptance pending")
    end
    function self:selectInfo(name)
        local info=assert(self.info[name],"installed mod info unavailable")
        self.content:ClearChildren()
        for address,record in pairs(self.rows) do if record.role~="info_select" then self.rows[address]=nil end end
        add(self.content,label(info.name))
        add(self.content,label(info.version and "Version " .. info.version or "Version not provided"))
        if info.support then
            local row=buttonRow(info.support,"support")
            self.rows[row:GetAddress()].url=info.support
            add(self.content,row)
        else add(self.content,label("Support link not provided")) end
    end
    function self:close()
        model:cancel()
        if ui.valid(self.widget) then self.widget:RemoveFromParent();assert(not self.widget:IsInViewport(),"settings panel removal failed") end
        if ui.valid(self.root) and ui.valid(self.pc) then
            StaticFindObject("/Script/UMG.Default__WidgetBlueprintLibrary"):SetInputMode_GameAndUIEx(self.pc,self.root,0,false,false)
            self.root:SetKeyboardFocus();self.pc.bShowMouseCursor=self.cursor
        end
        self.widget=nil;self.error=nil;self.rows={};self.selectors={}
        self.selection_requested=nil
    end
    function self:open(root,pc,mode)
        assert(not model.pending,"previous settings apply still pending")
        if ui.valid(self.widget) and self.widget:IsInViewport() then return end
        self.mode=mode or "settings"
        assert(self.mode=="settings" or self.mode=="info","unknown mod panel mode")
        model:open();self.root,self.pc,self.cursor=root,pc,pc.bShowMouseCursor
        self.widget=ui.create(PANEL,root,pc)
        self.widget.bIsFocusable=true
        local canvas=ui.child("CanvasPanel","CanvasPanel_43",self.widget)
        local border=ui.child("Border","Border_103",self.widget)
        local font=ui.child("TextBlock","TextBlock_2",self.widget).Font
        font.Size=20
        self.font=font
        canvas:ClearChildren()
        local slot=canvas:AddChildToCanvas(border)
        slot:SetAnchors({Minimum={X=0.08,Y=0.12},Maximum={X=0.92,Y=0.88}})
        slot:SetOffsets({Left=0,Top=0,Right=0,Bottom=0})
        local container=ui.native("VerticalBox",self.widget.WidgetTree)
        border:SetContent(container)
        add(container,label(self.mode=="info" and "Mod Info" or "Mod Settings"))
        local columns=ui.native("HorizontalBox",self.widget.WidgetTree)
        local columnSlot=add(container,columns);columnSlot:SetSize({Value=1,SizeRule=1})
        local leftSize=ui.native("SizeBox",self.widget.WidgetTree);leftSize:SetWidthOverride(280)
        local leftScroll=ui.native("ScrollBox",self.widget.WidgetTree)
        self.left=ui.native("VerticalBox",self.widget.WidgetTree)
        leftScroll:AddChild(self.left);leftSize:SetContent(leftScroll);columns:AddChildToHorizontalBox(leftSize)
        local rightScroll=ui.native("ScrollBox",self.widget.WidgetTree)
        self.content=ui.native("VerticalBox",self.widget.WidgetTree)
        rightScroll:AddChild(self.content)
        columns:AddChildToHorizontalBox(rightScroll):SetSize({Value=1,SizeRule=1})
        self.rows={};self.selectors={}
        local snapshots=mod.registry:list()
        local installed={}
        if self.mode=="info" then
            installed=require("mod_info").list(directory,mod.registry,function(level,message) mod:log(level,message) end)
            self.info={}
            for _,entry in ipairs(installed) do
                self.info[entry.name]=entry
                local row=buttonRow(entry.name,"info_select")
                self.rows[row:GetAddress()].name=entry.name
                self.selectors[#self.selectors+1]=row;add(self.left,row)
            end
        else
            for _,snapshot in ipairs(snapshots) do
                local id=snapshot.definition.id
                local row=buttonRow(snapshot.definition.name,"select")
                self.rows[row:GetAddress()].id=id;self.selectors[#self.selectors+1]=row
                add(self.left,row)
            end
        end
        self.error=label("");self.error:SetAutoWrapText(true);add(container,self.error)
        local footer=ui.native("HorizontalBox",self.widget.WidgetTree)
        for _,entry in ipairs({{self.widget.Apply_B,"Apply"},{self.widget.Cancel_B,"Cancel"},{self.widget.DeleteSave_B,"Defaults"}}) do
            entry[1]:RemoveFromParent();ui.buttonLabel(entry[1],entry[2],self.font)
            footer:AddChildToHorizontalBox(entry[1]):SetPadding({Left=0,Top=4,Right=16,Bottom=4})
            for _,brush in ipairs({"Normal","Hovered","Pressed","Disabled"}) do entry[1].WidgetStyle[brush].DrawAs=0 end
        end
        add(container,footer)
        if self.mode=="info" then
            self.widget.Apply_B:SetVisibility(1);self.widget.DeleteSave_B:SetVisibility(1)
            ui.buttonLabel(self.widget.Cancel_B,"Close")
            if #installed>0 then self:selectInfo(installed[1].name) end
        elseif #snapshots>0 then self:select(snapshots[1].definition.id) else add(self.content,label("No registered mods")) end
        self.widget:AddToViewport(100)
        assert(self.widget:IsInViewport(),"settings panel viewport attachment failed")
        StaticFindObject("/Script/UMG.Default__WidgetBlueprintLibrary"):SetInputMode_UIOnlyEx(pc,self.widget,0,false)
        pc.bShowMouseCursor=true;self.widget:SetKeyboardFocus()
        mod:log("info","settings panel attached; input and visual acceptance pending")
    end
    local function rowPressed(context,direction)
        if self.rendering or model.pending then return end
        local record=self.rows[context:get():GetAddress()]
        if not record then return end
        if record.role=="select" then self.selection_requested={id=record.id}
        elseif record.role=="info_select" then self.selection_requested={name=record.name}
        elseif record.role=="support" then
            assert(ui.valid(StaticFindObject("/Script/Engine.KismetSystemLibrary:LaunchURL")),"support URL function unavailable")
            StaticFindObject("/Script/Engine.Default__KismetSystemLibrary"):LaunchURL(record.url)
        elseif record.role=="action" then model:action(record.id,record.field.key);status()
        elseif record.role=="choice" then
            record.index=(record.index-1+direction)%#record.field.options+1
            local option=record.field.options[record.index]
            model:edit(record.id,record.field.key,option.value);ui.text(record.widget.OptionType_T,option.label);status()
        end
    end
    mod:bind(CHOICE .. ":BndEvt__CabinChoiceRow_LeftArrow_B_K2Node_ComponentBoundEvent_0_OnButtonPressedEvent__DelegateSignature",function(context) rowPressed(context,-1) end)
    mod:bind(CHOICE .. ":BndEvt__CabinChoiceRow_RightArrow_B_K2Node_ComponentBoundEvent_1_OnButtonPressedEvent__DelegateSignature",function(context) rowPressed(context,1) end)
    mod:bind(BOOL .. ":BndEvt__CabinBoolRow_CheckBox_129_K2Node_ComponentBoundEvent_2_OnCheckBoxComponentStateChanged__DelegateSignature",function(context,value)
        if self.rendering or model.pending then return end
        local record=self.rows[context:get():GetAddress()]
        if record then model:edit(record.id,record.field.key,value:get());status() end
    end)
    mod:bind(NUMBER .. ":CabinTextChanged",function(context,text)
        if self.rendering or model.pending then return end
        local record=self.rows[context:get():GetAddress()]
        if record then
            local bytes=text:get():ToString()
            local value=tonumber(bytes)
            model:edit(record.id,record.field.key,value or bytes);status()
        end
    end)
    for _,entry in ipairs({
        {"BndEvt__CabinSettingsPanel_Apply_B_K2Node_ComponentBoundEvent_13_OnButtonPressedEvent__DelegateSignature",function() model:applyAll();status() end},
        {"BndEvt__CabinSettingsPanel_Cancel_B_K2Node_ComponentBoundEvent_12_OnButtonPressedEvent__DelegateSignature",function() self:close() end},
        {"BndEvt__CabinSettingsPanel_Apply_B_1_K2Node_ComponentBoundEvent_3_OnButtonPressedEvent__DelegateSignature",function() if self.selected then model:defaults(self.selected);self.selection_requested={id=self.selected} end end},
    }) do
        mod:bind(PANEL .. ":" .. entry[1],function(context)
            if ui.valid(self.widget) and context:get():GetAddress()==self.widget:GetAddress() then entry[2]() end
        end)
    end
    mod:bind("/Script/UMG.UserWidget:OnPreviewKeyDown",function(context,geometry,event)
        if not ui.valid(self.widget) or not self.widget:IsInViewport() then return end
        local widget=context:get()
        if not ui.valid(widget) or widget:GetWorld():GetAddress()~=self.widget:GetWorld():GetAddress() then return end
        local key=StaticFindObject("/Script/Engine.Default__KismetInputLibrary"):GetKey(event:get())
        if key.KeyName:ToString()=="Escape" then self:close();return StaticFindObject("/Script/UMG.Default__WidgetBlueprintLibrary"):Handled() end
    end)
    mod:observe("settings acknowledgement",function()
        model:poll();status()
        local requested=self.selection_requested
        if requested and not model.pending and ui.valid(self.widget) and self.widget:IsInViewport() then
            self.selection_requested=nil
            if requested.id then self:select(requested.id) else self:selectInfo(requested.name) end
        end
    end)
    return self
end
return M
