local ui=require("ui")
local M={}
local PREFIX="/Game/CabinModSettings/"
local CARD=PREFIX .. "MenuCardModSettings_WBP.MenuCardModSettings_WBP_C"
local function asset(name,kind) return ui.load(PREFIX .. name .. "." .. name .. (kind=="class" and "_C" or ""),kind) end
function M.start(mod)
    if os.getenv("CABIN_REJOIN_PROCESS_ID") then mod:log("info","settings UI skipped for Rejoin authority");return end
    local panel=require("settings_panel").start(mod)
    local state
    mod:bind(CARD .. ":BndEvt__MenuCardModSettings_WBP_Host_B_K2Node_ComponentBoundEvent_2_OnButtonPressedEvent__DelegateSignature",function(context)
        if state and ui.valid(state.card) and context:get():GetAddress()==state.card:GetAddress() then panel:open(state.root,state.pc) end
    end)
    mod:observe("main menu card",function()
        local root
        for _,value in ipairs(FindAllOf("Menu_WBP_C") or {}) do
            if ui.valid(value) and value:IsInViewport() then assert(not root,"main menu root ambiguous");root=value end
        end
        if not root then state=nil;return end
        if state and state.root:GetAddress()==root:GetAddress() and ui.valid(state.card) then
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
        local pc=root:GetOwningPlayer()
        assert(ui.valid(pc) and pc:IsLocalController(),"settings card local owner unavailable")
        local transform=original:GetTransform()
        local gap=profile:GetTransform().Translation.Y-transform.Translation.Y
        assert(gap>0,"original card spacing invalid")
        transform.Translation.Y=transform.Translation.Y+3*gap
        local card=ui.create(CARD,root,pc)
        for _,name in ipairs({"Single_B","Join_B","Single_Progressbar","Join_Progressbar"}) do
            assert(ui.valid(card[name]),"unused menu control missing");card[name]:SetVisibility(2)
        end
        card.Host_B:SetVisibility(2)
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
        local front,back=actor.Widget:GetWidget(),actor.WidgetBackside:GetWidget()
        for index,renderer in ipairs({front,back}) do
            assert(ui.valid(renderer),"settings card renderer missing")
            renderer.Backside=index==2
            renderer.VerticalBoxFront:SetVisibility(index==1 and 0 or 2)
            renderer.VerticalBoxBack:SetVisibility(index==1 and 2 or 0)
            ui.text(ui.child("TextBlock","Title_1",renderer),"Mod Settings")
            renderer.VerticalBoxBack:SetVisibility(2)
            renderer.VerticalBoxFront:SetVisibility(0)
        end
        local border=ui.child("Border","Border_42",card)
        border:SetBrushFromMaterial(asset("M_RT_MenuCardModSettings","object"))
        actor:FlipStart_E();capture:CaptureScene()
        require("cabin_menu_layout").attach(root,row,"settings",card,"right")
        state={root=root,pc=pc,card=card,actor=actor,hovered=false}
        mod:log("info","Mod Settings card attached right; original identities retained; visual acceptance pending")
    end)
    return panel
end
return M
