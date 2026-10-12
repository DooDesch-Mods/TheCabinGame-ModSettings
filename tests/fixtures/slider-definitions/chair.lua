return {id="cabin_chair_marker",name="CabinChairMarker",fields={
    {key="enabled",label="Enabled",type="boolean",default=true},
    {key="style",label="Style",type="choice",default="blood",options={
        {value="blood",label="Blood"},{value="cross",label="Cross"},{value="circle",label="Circle"},
    }},
    {key="size",label="Size",type="number",default=18,min=5,max=30},
    {key="seat",label="Seat",type="boolean",default=true},
    {key="back",label="Backrest",type="boolean",default=true},
}}
