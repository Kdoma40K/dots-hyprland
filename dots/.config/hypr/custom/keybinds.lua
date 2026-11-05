hl.bind("CTRL+SUPER+ALT+Slash", hl.dsp.exec_cmd("xdg-open ~/.config/hypr/custom/keybinds.lua"), {description = "Edit user keybinds"} )

-- nasa-punk: Panacea muscle memory, ported from kdoma's live config.
-- Reads: nothing. Loaded by hyprland.lua after hyprland/keybinds.lua, which is
-- why the unbinds below can see end-4's defaults.
-- SUPER+T needs no entry: end-4 already opens the terminal there, and a second
-- bind would stack and open two terminals.

-- Binds on one combo stack and all fire, so clear end-4's action first.
-- Replaces "App: Code editor". SUPER+Q still closes too.
hl.unbind("SUPER + C")
hl.bind("SUPER + C", hl.dsp.window.close(), { description = "Window: Close" })

-- Replaces a duplicate left sidebar toggle. SUPER+A and SUPER+O still open it.
-- Named directly because end-4's browser list tries Chrome and Firefox first.
hl.unbind("SUPER + B")
hl.bind("SUPER + B", hl.dsp.exec_cmd("vivaldi-stable"), { description = "App: Browser" })
