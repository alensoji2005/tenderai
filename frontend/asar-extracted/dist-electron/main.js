import { BrowserWindow as e, app as t, ipcMain as n } from "electron";
import { fileURLToPath as r } from "node:url";
import i from "node:path";
//#region electron/main.js
var a = i.dirname(r(import.meta.url));
process.env.APP_ROOT = i.join(a, "..");
var o = process.env.VITE_DEV_SERVER_URL, s = i.join(process.env.APP_ROOT, "dist-electron"), c = i.join(process.env.APP_ROOT, "dist");
process.env.VITE_PUBLIC = o ? i.join(process.env.APP_ROOT, "public") : c;
var l;
function u() {
	l = new e({
		width: 1200,
		height: 800,
		minWidth: 900,
		minHeight: 600,
		frame: !1,
		titleBarStyle: "hidden",
		webPreferences: {
			preload: i.join(a, "preload.mjs"),
			contextIsolation: !0,
			nodeIntegration: !1
		}
	}), n.on("window-min", () => l.minimize()), n.on("window-max", () => {
		l.isMaximized() ? l.unmaximize() : l.maximize();
	}), n.on("window-close", () => l.close()), o ? l.loadURL(o) : l.loadFile(i.join(c, "index.html"));
}
t.on("window-all-closed", () => {
	process.platform !== "darwin" && (t.quit(), l = null);
}), t.on("activate", () => {
	e.getAllWindows().length === 0 && u();
}), t.whenReady().then(u);
//#endregion
export { s as MAIN_DIST, c as RENDERER_DIST, o as VITE_DEV_SERVER_URL };
