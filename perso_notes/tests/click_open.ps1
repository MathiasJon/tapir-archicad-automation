Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
Add-Type @"
using System; using System.Runtime.InteropServices;
public class M4 { [DllImport("user32.dll")] public static extern bool SetCursorPos(int x,int y); [DllImport("user32.dll")] public static extern void mouse_event(int f,int x,int y,int d,int e); [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h); }
"@
$root=[System.Windows.Automation.AutomationElement]::RootElement
for($i=0;$i -lt 40;$i++){
  Start-Sleep -Milliseconds 700
  $p=Get-Process -Name Archicad -ErrorAction SilentlyContinue | Select-Object -First 1; if(-not $p){continue}
  $w=$root.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition) | Where-Object { $_.Current.ProcessId -eq $p.Id } | Select-Object -First 1
  if(-not $w){continue}
  $dlg=$w.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition) | Where-Object { $_.Current.Name -like "Ouvrir*.pla" } | Select-Object -First 1
  if(-not $dlg){continue}
  $btn=$dlg.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition) | Where-Object { $_.Current.Name -eq "Ouvrir" } | Select-Object -First 1
  if(-not $btn){continue}; $r=$btn.Current.BoundingRectangle; if($r.Width -le 0){continue}
  [M4]::SetForegroundWindow([IntPtr]$w.Current.NativeWindowHandle) | Out-Null; Start-Sleep -Milliseconds 300
  [M4]::SetCursorPos([int]($r.X+$r.Width/2),[int]($r.Y+$r.Height/2)) | Out-Null; Start-Sleep -Milliseconds 150; [M4]::mouse_event(2,0,0,0,0); [M4]::mouse_event(4,0,0,0,0)
  "clicked"; exit
}
"no dialog"
