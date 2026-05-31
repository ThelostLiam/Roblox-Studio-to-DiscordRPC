local HttpService = game:GetService("HttpService")
local ScriptEditorService = game:GetService("ScriptEditorService")
local Selection = game:GetService("Selection")

local SERVER_URL = "http://localhost:3000/update"
local COOLDOWN_TIME = 3
local lastUpdate = 0

local function getSessionContext()
	if game.PlaceId > 0 then
		return "Cloud Session"
	else
		return "Local Project"
	end
end

local function sendPresenceUpdate()
	if os.time() - lastUpdate < COOLDOWN_TIME then return end
	lastUpdate = os.time()

	local projectName = (game.Name ~= "The Big Game" and game.Name ~= "Place") and game.Name or "Unsaved Place"
	local currentActivity = "Browsing Explorer"
	local sessionType = getSessionContext()

	-- FIXED: Swapped GetActiveScript() for the correct native GetCurrentScript()
	local success, activeScript = pcall(function()
		return ScriptEditorService:GetCurrentScript()
	end)

	if success and activeScript then
		currentActivity = "Editing: " .. activeScript.Name .. ".lua"
	else
		-- Selection Context Fallback
		local currentSelection = Selection:Get()
		if #currentSelection > 0 then
			currentActivity = "Modifying: " .. currentSelection[1].Name
		end
	end

	local payload = {
		details = currentActivity,
		state = "Project: " .. projectName .. " (" .. sessionType .. ")"
	}

	task.spawn(function()
		local httpSuccess, result = pcall(function()
			return HttpService:PostAsync(SERVER_URL, HttpService:JSONEncode(payload), Enum.HttpContentType.ApplicationJson)
		end)
		if not httpSuccess then
			warn("[Studio Status Syncer] Local daemon offline or port 3000 blocked.")
		end
	end)
end

ScriptEditorService.TextDocumentDidChange:Connect(sendPresenceUpdate)
Selection.SelectionChanged:Connect(sendPresenceUpdate)

print("Roblox Studio Syncer is active!")
