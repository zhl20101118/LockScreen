#include <windows.h>
#include <shellapi.h>
#include<bits/stdc++.h>
using namespace std;
string EXE_PATH = "D:\\1My_Computer_Lock\\lockscreen.exe";
HHOOK g_hHook = NULL;
bool g_winPressed = false;
DWORD g_lastTriggerTime = 0;
const DWORD COOLDOWN_MS = 10000;

LRESULT CALLBACK LowLevelKeyboardProc(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode == HC_ACTION) {
        KBDLLHOOKSTRUCT* pKb = (KBDLLHOOKSTRUCT*)lParam;
        if (pKb->vkCode == VK_LWIN || pKb->vkCode == VK_RWIN) {
            if (wParam == WM_KEYDOWN || wParam == WM_SYSKEYDOWN)
                g_winPressed = true;
            else if (wParam == WM_KEYUP || wParam == WM_SYSKEYUP)
                g_winPressed = false;
        }
        if ((wParam == WM_KEYDOWN || wParam == WM_SYSKEYDOWN) && pKb->vkCode == 'A' && g_winPressed) {
            DWORD now = GetTickCount();
            if (g_lastTriggerTime == 0 || (now - g_lastTriggerTime) >= COOLDOWN_MS) {
                string cmd= "start " + EXE_PATH;
                g_lastTriggerTime = now;
				system(cmd.c_str());
//				Sleep(5000);
				cmd="start recognize.exe";
                system(cmd.c_str());
//				ShellExecuteW(NULL, L"open", EXE_PATH, NULL, NULL, SW_SHOW);
            }
        }
    }
    return CallNextHookEx(g_hHook, nCode, wParam, lParam);
}

int main() {
HWND hWnd = GetConsoleWindow(); // 获取控制台窗口的句柄
ShowWindow(hWnd, SW_HIDE); // 隐藏控制台窗口
// ... 其他代码

    g_hHook = SetWindowsHookExW(WH_KEYBOARD_LL, LowLevelKeyboardProc, GetModuleHandleW(NULL), 0);
    if (!g_hHook) return 1;

    MSG msg;
    while (GetMessageW(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }

    UnhookWindowsHookEx(g_hHook);
    return 0;
}
