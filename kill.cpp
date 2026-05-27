#include<bits/stdc++.h>
#include <conio.h>
#include<windows.h>
#include<time.h>
#include<tlhelp32.h>
#include<iostream>
#include<map>
#include<string>
#include<thread>
#include <psapi.h>
#pragma comment(lib, "psapi.lib")
#pragma comment(lib, "kernel32.lib")

using namespace std;


const int Year=2025,Month=10,Day=22;


void killProcess(DWORD pid) {
	HANDLE hProcess=OpenProcess(PROCESS_TERMINATE,FALSE,pid);
	if(hProcess) {
		TerminateProcess(hProcess,0);
		CloseHandle(hProcess);
	}
}
struct node {
	string rode,name;
};
unordered_map<string,int>mp;
vector<string>vv;
string S;
void bfs_kill() {
	HANDLE hSnapshot=CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0);
	if(hSnapshot) {
		PROCESSENTRY32 p;
		p.dwSize=sizeof(PROCESSENTRY32);
		if(Process32First(hSnapshot,&p)) {
			do {
				string s=p.szExeFile;
//				cout<<s<<endl;
				if(s==S) {
					killProcess(p.th32ProcessID);
				}
			} while(Process32Next(hSnapshot,&p));
		}
		CloseHandle(hSnapshot);
	}
}

int main(int argc,char* argv[]) {
	S="lockscreen.exe";
	bfs_kill();
	
	return 0;
}
