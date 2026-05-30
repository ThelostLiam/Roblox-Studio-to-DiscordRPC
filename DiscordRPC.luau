--Put this script in ServerScriptService in any Roblox Place, publish it as Roblox Local Plugin!

local HttpService = game:GetService("HttpService")
local Selection = game:GetService("Selection")
local ScriptEditorService = game:GetService("ScriptEditorService")

local SERVER_URL = "http://127.0.0.1:3000/update"
local lastUpdate = 0
local cooldown = 3 -- Dynamic real-time updates every 3 seconds

local currentDetails = "Idling in Studio"

local function sendUpdate(details, state)
	if os.time() - lastUpdate < cooldown then return end
	lastUpdate = os.time()

	local data = { details = details, state = state }
	task.spawn(function()
		pcall(function()
			HttpService:PostAsync(SERVER_URL, HttpService:JSONEncode(data), Enum.HttpContentType.ApplicationJson)
		end)
	end)
end

local function getTopService(obj)
	local current = obj
	while current and current.Parent ~= game do
		if current.Parent == nil then return "Unparented" end
		current = current.Parent
	end
	return current and current.Name or "Workspace"
end

-- Safely formats the game context
local function getGameContext()
	if game.PlaceId == 0 then
		return "Local Game" -- Hides your local filename or path entirely
	else
		return "Public Game: " .. game.Name -- Shows the actual name of published games
	end
end

ScriptEditorService.TextDocumentDidOpen:Connect(function(document)
	local scriptObj = document:GetScript()
	if scriptObj then
		local location = getTopService(scriptObj)
		local scriptType = "Script"

		if scriptObj:IsA("LocalScript") then scriptType = "LocalScript"
		elseif scriptObj:IsA("ModuleScript") then scriptType = "ModuleScript"
		end

		currentDetails = "Editing " .. scriptType .. " inside " .. location
		sendUpdate(currentDetails, getGameContext())
	end
end)
Selection.SelectionChanged:Connect(function()
	local selected = Selection:Get()
	if #selected > 0 then
		local location = getTopService(selected[1])
		currentDetails = "Modifying Assets in " .. location
	else
		-- If they cleared selection, check if they still have scripts open
		local openDocs = ScriptEditorService:GetScriptDocuments()
		if #openDocs > 0 then
			currentDetails = "Working on Scripts"
		else
			currentDetails = "Idling in Studio"
		end
	end
	sendUpdate(currentDetails, getGameContext())
end)
task.spawn(function()
	while true do
		local openDocs = ScriptEditorService:GetScriptDocuments()
		local selected = Selection:Get()

		-- If nothing is open and nothing is selected, you're idling
		if #openDocs == 0 and #selected == 0 then
			currentDetails = "Idling in Studio"
		end

		sendUpdate(currentDetails, getGameContext())
		task.wait(10)
	end
end)
