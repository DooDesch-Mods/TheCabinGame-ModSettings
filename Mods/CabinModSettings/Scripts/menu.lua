local ui=require("ui")
local M={}
local PREFIX="/Game/CabinModSettings/"
local CARD=PREFIX .. "MenuCardModSettings_WBP.MenuCardModSettings_WBP_C"
local function asset(name,kind) return ui.load(PREFIX .. name .. "." .. name .. (kind=="class" and "_C" or ""),kind) end
function M.start(mod,directory)
    if os.getenv("CABIN_REJOIN_PROCESS_ID") then mod:log("info","settings UI skipped for Rejoin authority");return end
    local panel=require("settings_panel").start(mod,directory)
    local state
    local intro_waiting
    local function prepareHover()
        local layout=state.hover_layout
        assert(ui.valid(state.actor) and ui.valid(layout.back),"settings hover renderer unavailable before layout")
        local function widths()
            layout.back:ForceLayoutPrepass()
            layout.reference:ForceLayoutPrepass()
            local values={}
            local referenceWidth=layout.reference.Host_T:GetDesiredSize().X
            assert(type(referenceWidth)=="number" and referenceWidth==referenceWidth and referenceWidth>=0 and referenceWidth<math.huge,"settings hover reference text width invalid: Social Credits")
            if referenceWidth==0 then return end
            values.reference=referenceWidth
            for index,entry in ipairs(layout.entries) do
                local width=entry.label:GetDesiredSize().X
                assert(type(width)=="number" and width==width and width>=0 and width<math.huge,"settings hover text width invalid: " .. entry.button)
                if width==0 then return end
                values[index]=width
            end
            return values
        end
        local measured=widths()
        if not measured then
            layout.waits=(layout.waits or 0)+1
            assert(layout.waits<=30,"settings hover layout unavailable after 30 observations: native text desired width is zero; card not attached")
            if layout.waits==1 then mod:log("info","settings hover layout waiting: native text desired width is zero") end
            return
        end
        for index,entry in ipairs(layout.entries) do
            local slot=state.card[entry.button].Slot
            assert(ui.valid(slot) and slot:IsA("/Script/UMG.CanvasPanelSlot"),"settings hover canvas slot unavailable: " .. entry.button)
            local size,position=slot:GetSize(),slot:GetPosition()
            -- Match Social Credits while preserving each option's native center.
            local width=layout.reference_button.Slot:GetSize().X*measured[index]/measured.reference
            assert(width>0 and width<math.huge,"settings hover button width invalid: " .. entry.button)
            local left=position.X+(size.X-width)/2
            slot:SetSize({X=width,Y=size.Y})
            slot:SetPosition({X=left,Y=position.Y})
            local observedSize,observedPosition=slot:GetSize(),slot:GetPosition()
            assert(math.abs(observedSize.X-width)<0.01 and math.abs(observedSize.Y-size.Y)<0.01 and math.abs(observedPosition.X-left)<0.01 and math.abs(observedPosition.Y-position.Y)<0.01,"settings hover geometry readback differs: " .. entry.button)
        end
        if layout.waits then mod:log("info","settings hover layout recovered after " .. layout.waits .. " waits") end
        state.actor:FlipStart_E();state.actor.SceneCaptureComponent2D:CaptureScene()
        require("cabin_menu_layout").attach(state.root,layout.row,"settings",state.card,"right")
        state.hover_layout=nil
        mod:log("info","Mod Settings card attached right; native hover widths read back; visual acceptance pending")
    end
    local function request(context,mode)
        if state and ui.valid(state.card) and context:get():GetAddress()==state.card:GetAddress() then
            state.open_requested=mode
            mod:log("info",mode .. " panel open requested")
        end
    end
    mod:bind(CARD .. ":BndEvt__MenuCardModSettings_WBP_Single_B_K2Node_ComponentBoundEvent_0_OnButtonPressedEvent__DelegateSignature",function(context) request(context,"settings") end)
    mod:bind(CARD .. ":BndEvt__MenuCardModSettings_WBP_Host_B_K2Node_ComponentBoundEvent_2_OnButtonPressedEvent__DelegateSignature",function(context) request(context,"info") end)
    mod:observe("main menu card",function()
        local root
        for _,value in ipairs(FindAllOf("Menu_WBP_C") or {}) do
            if ui.valid(value) and value:IsInViewport() then assert(not root,"main menu root ambiguous");root=value end
        end
        if not root then state=nil;return end
        if state and state.root:GetAddress()==root:GetAddress() and ui.valid(state.card) then
            if state.hover_layout then prepareHover();return end
            if state.open_requested then
                local mode=state.open_requested
                state.open_requested=nil
                panel:open(state.root,state.pc,mode)
            end
            local hovered=state.card:IsHovered()
            if hovered then state.return_front=nil
            elseif state.hovered then state.return_front=true end
            state.hovered=hovered
            if state.return_front and not state.actor.Disabled then
                state.card:Unhovered_E()
                assert(not state.actor.PlayFlip and state.actor.Flip_TL:IsReversing(),"settings hover return readback differs")
                state.return_front=nil
            end
            if hovered then
                for _,entry in ipairs({
                    {root.MenuCardPlay_WBP,"Play_Card","Unhovered_E"},
                    {root.MenuCardProfile_WBP,"Profile_Card","Unhover_E"},
                    {root.MenuCardSocial_WBP,"Social_Card","Unhovered_E"},
                }) do
                    local widget=entry[1]
                    local actor=widget[entry[2]]
                    if ui.valid(actor) and not widget:IsHovered() and actor.PlayFlip and not actor.Disabled then
                        widget[entry[3]](widget)
                        assert(not actor.PlayFlip and actor.Flip_TL:IsReversing(),"original menu hover return readback differs")
                    end
                end
            end
            return
        end
        local row=root["3CardsHorizBox"]
        if not ui.valid(row) or row:GetChildrenCount()<3 then return end
        local original,profile=root.MenuCardPlay_WBP.Play_Card,root.MenuCardProfile_WBP.Profile_Card
        if not ui.valid(original) or not ui.valid(profile) then return end
        local social=root.MenuCardSocial_WBP.Social_Card
        assert(ui.valid(social) and ui.valid(social.FlipStart_TL) and ui.valid(social.CardMesh),"settings card original Social intro target unavailable")
        -- ShowCard_E staggers the original cards by this timeline interval.
        if not social.CardMesh:IsVisible() or social.FlipStart_TL:GetPlaybackPosition()<0.15 then
            if not intro_waiting then mod:log("info","settings card waiting for native Social intro reveal");intro_waiting=true end
            return
        end
        if intro_waiting then mod:log("info","settings card native Social intro reveal observed");intro_waiting=nil end
        local pc=root:GetOwningPlayer()
        assert(ui.valid(pc) and pc:IsLocalController(),"settings card local owner unavailable")
        local transform=original:GetTransform()
        local gap=profile:GetTransform().Translation.Y-transform.Translation.Y
        assert(gap>0,"original card spacing invalid")
        transform.Translation.Y=transform.Translation.Y+3*gap
        local card=ui.create(CARD,root,pc)
        for _,name in ipairs({"Join_B","Join_Progressbar"}) do
            assert(ui.valid(card[name]),"unused menu control missing");card[name]:SetVisibility(2)
        end
        card.Single_B:SetVisibility(0)
        card.Host_B:SetVisibility(0)
        local gameplay=StaticFindObject("/Script/Engine.Default__GameplayStatics")
        local actorClass=asset("MenuCard_ModSettings","class")
        local actor=gameplay:BeginDeferredActorSpawnFromClass(root,actorClass,transform,1,nil,0)
        assert(ui.valid(actor),"settings card actor spawn failed")
        actor=gameplay:FinishSpawningActor(actor,transform,0)
        assert(ui.valid(actor),"settings card actor finish failed")
        card.Play_Card=actor
        local rt=asset("RT_MenuCardModSettings","object")
        local capture=actor.SceneCaptureComponent2D
        assert(ui.valid(capture) and capture.TextureTarget:GetAddress()==rt:GetAddress(),"settings card render target differs")
        capture.PrimitiveRenderMode=2;capture:ClearShowOnlyComponents();capture:ShowOnlyActorComponents(actor,true)
        local front=actor.Widget:GetWidget()
        assert(ui.valid(front),"settings front renderer missing")
        local rendererPath=assert(front:GetClass():GetFullName():match("^[^ ]+ (.+)$"),"renderer class path unavailable")
        actor.WidgetBackside:SetWidget(ui.create(rendererPath,root,pc))
        local back=actor.WidgetBackside:GetWidget()
        assert(ui.valid(front) and ui.valid(back),"settings card renderer missing")
        assert(front:GetAddress()~=back:GetAddress() and front:GetClass():GetAddress()==back:GetClass():GetAddress(),"settings renderer instances/class differ")
        for index,renderer in ipairs({front,back}) do
            renderer.Backside=index==2
            renderer.VerticalBoxFront:SetVisibility(index==1 and 0 or 2)
            renderer.VerticalBoxBack:SetVisibility(index==1 and 2 or 0)
            ui.text(ui.child("TextBlock","Title_1",renderer),"Mods")
            ui.text(ui.child("TextBlock","Single_T",renderer),"Settings")
            ui.text(ui.child("TextBlock","Host_T",renderer),"Info")
            ui.child("TextBlock","JoinT",renderer):SetVisibility(1)
            ui.child("Image","Image_1",renderer):SetVisibility(1)
        end
        local border=ui.child("Border","Border_42",card)
        border:SetBrushFromMaterial(asset("M_RT_MenuCardModSettings","object"))
        local reference=social.WidgetBackside:GetWidget()
        assert(ui.valid(reference) and reference:GetClass():GetFullName()=="WidgetBlueprintGeneratedClass /Game/MenuContent/3DMenuCards/MenuCardSocial_W.MenuCardSocial_W_C" and ui.valid(reference.Host_T),"settings hover original Social Credits renderer unavailable")
        local referenceButton=root.MenuCardSocial_WBP.Credits_B
        assert(ui.valid(referenceButton) and ui.valid(referenceButton.Slot) and referenceButton.Slot:IsA("/Script/UMG.CanvasPanelSlot"),"settings hover original Social Credits button unavailable")
        state={root=root,pc=pc,card=card,actor=actor,hovered=false,hover_layout={
            back=back,reference=reference,reference_button=referenceButton,row=row,entries={
                {button="Single_B",label=ui.child("TextBlock","Single_T",back)},
                {button="Host_B",label=ui.child("TextBlock","Host_T",back)},
            },
        }}
        prepareHover()
    end)
    return panel
end
return M
