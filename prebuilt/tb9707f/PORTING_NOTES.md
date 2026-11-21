# TB-9707F (Legion Y700 一代) 移植笔记

目标：把联想小新 Pad Pro 12.6（`TB-Q706F`，骁龙 870 / SM8250 / kona，Linux 4.19）的开源内核
移植到 **拯救者 Y700 一代（`TB-9707F`）**，并在 GitHub Actions 上完成云端编译与 AnyKernel3 打包。

真机采集于 2026-11-21，活动槽位 `_a`，系统
`TB-9707F_CN_OPEN_USER_Q00024.0_T_ZUI_15.0.418_ST_240116`（Android 13，安全补丁 2023-11-01）。
采集产物在设备侧 `/data/local/tmp/y700_port_work/extracted/`（`stock_boot.img`、
`stock_dtbo.img` 等大文件不入库），进入仓库的只有 `prebuilt/tb9707f/dtb` 与本目录的元数据。

## 1. 内核与 boot 基线

| 项目 | 值 |
|---|---|
| 内核版本 | `4.19.157-perf+`，`#1 SMP PREEMPT Tue Jan 16 07:48:08 CST 2024` |
| 原厂编译器 | `clang version 10.0.7 for Android NDK` + GNU ld 2.27 |
| vermagic | `4.19.157-perf+ SMP preempt mod_unload modversions aarch64` |
| boot header | v2，pagesize 4096，base `0x00000000`，kernel `0x8000`，ramdisk `0x01000000`，tags `0x0100`，dtb `0x01f00000` |
| os_version | `11.0.0` / patch `2023-11`（原厂写死为 11.0.0，与实机 Android 13 不一致，属正常现象） |
| DTB | 1606983 B，内容 = 3 个 kona 基础 DTB + 1 个 173 B 占位，**不含 panel/touch 节点** |
| DTBO | 25165824 B，13 个 overlay，屏幕/触控/充电节点都在这里 |

结论：**panel 与 touch 的 DT 节点全部来自 `dtbo` 分区**，刷机时绝不能动 `dtbo`，
内核只负责提供与之匹配的驱动与 display techpack。

## 2. 硬件特征

| 部件 | 型号/证据 |
|---|---|
| 屏幕 | Novatek **NT36523** LCD，DT 节点 `qcom,mdss_dsi_nt36523_panel_vid`，dual-DSI + DSC，`1600x2560@120Hz`（`/sys/class/drm/card0-DSI-1/modes`） |
| 触控 | Novatek **NVT-ts**，走 **SPI**：`/sys/bus/spi/devices/spi0.0 -> spi:NVT-ts-spi`，驱动 `NVT-ts` |
| 手写笔 | `NVTCapacitivePen`（`/proc/bus/input/devices`） |
| 电池 | `bq27541-0`（TI 电量计）+ `bms`/`battery`（qcom） |
| 旁路充电 | `/sys/class/qcom-battery/restrict_chg`、`restrict_cur`（ZUI 的「旁路充电」策略节点），配合 `battery/input_suspend`、`usb/input_current_now` |
| 其它输入 | `game_mode_switcher`（游戏模式拨键）、`qpnp_pon`、`gpio-keys`、`qti-haptics` |
| Wi-Fi | `qca_cld3_qca6390.ko`（`/vendor/lib/modules`，41 个 .ko 全部为 `4.19.157-perf+`） |
| 联想私有模块 | `lcd.ko`（`name=lcd intree=Y`），依赖联想补丁导出的符号 |

## 3. 源码树里不存在的联想私有 `CONFIG_*`

`/proc/config.gz` 中有 13 个符号在本仓库全部 Kconfig 里都找不到，已从
`tb9707f_defconfig` 剔除（生成器：`tools/tb9707f/kconfig_filter.py`）：

| 符号 | 原意 | 缺失后果 |
|---|---|---|
| `TOUCHSCREEN_NT36xxx_HOSTDL_SPI` | 联想版 NT36xxx，SPI + HostDL 固件下载 | **触摸不可用**（本树只有 I2C 版 `TOUCHSCREEN_NT36XXX`，匹配不到 `novatek,NVT-ts-spi`） |
| `GAME_MODE_SWITCHER` | 游戏模式拨键驱动 | 拨键无输入 |
| `AW8697_HAPTIC` | AW8697 触觉驱动 | 振动/触感反馈缺失 |
| `DRV2667` | TI DRV2667 触觉 | 同上 |
| `USB_REDRIVER_PI2DPX1217` | USB redriver | USB 信号质量/充电协商可能异常 |
| `CHARGE_FULL_SCALE` | 满电容量换算 | 电量显示精度 |
| `WT_USB_BURN` / `WT_COMPILE_FACTORY_VERSION` | Wingtech 工厂烧录/工厂版 | 产线功能，日常无用 |
| `MSM_RELEASE_BUILD` | 发行构建标记 | 仅影响版本串 |

> 注意：`GAME_MODE_SWITCHER` 在实机上已注册为输入设备，说明原厂内核确实带该驱动；
> 本仓库没有对应源码，属于**上游开源包缺件**，不是配置错误。

## 4. 已知风险与待办

1. **触摸（最高优先级）**：需要把 `drivers/input/touchscreen/nt36xxx/` 扩展成 SPI 传输
   （`of_match` 增加 `novatek,NVT-ts-spi`，`spi_driver` + bus 抽象），并按 HostDL 流程加载固件。
   当前内核即使能开机，触摸也不会工作。
2. **`dtbs` 无法从源码构建**：`arch/arm64/boot/dts/vendor` 是指向
   `vendor/qcom/proprietary/devicetree-4.19` 的**悬空符号链接**，联想未公开该目录。
   因此 `make dtbs` 只会产出空集，打包统一使用 `prebuilt/tb9707f/dtb`（与原机 boot 内一致）。
3. **`lcd.ko` 可能加载失败**：它依赖联想私有导出的符号（`lcd` 相关 notifier）。
   若 `insmod` 报 `Unknown symbol`，属预期，不影响基本显示。
4. **`CONFIG_KPROBES` 原厂为关闭**（`# CONFIG_KPROBES is not set`）。KernelSU 的 kprobe
   方案需要它，CI 在 `use_kernelsu=true` 时会自动打开。
5. **panel 依赖 stock dtbo**：任何刷机脚本都不得写 `dtbo`；`anykernel.sh` 里
   `do.dtbo=0`、`BLOCK=boot`、`IS_SLOT_DEVICE=1`。

## 5. vermagic 对齐（Wi-Fi 能否加载的关键）

原厂模块 vermagic 为 `4.19.157-perf+`，其中的 `+` 由 `scripts/setlocalversion`
在「git 树不干净」时追加。云端构建一旦改动工作树（例如 KernelSU 注入），就会多出
一个 `+` 变成 `4.19.157-perf++`，Wi-Fi 模块随即拒绝加载。

因此：
- `CONFIG_LOCALVERSION` 保持原厂值 `"-perf"`；
- CI 在编译前写入 `.scmversion`（内容仅一个 `+`，无换行），把后缀钉死；
- CI 用 `make -s kernelrelease` 断言结果必须等于 `4.19.157-perf+`，不等直接失败；
- `# CONFIG_MODULE_SIG_FORCE is not set`，否则原厂签名模块无法加载。

## 6. 云端构建

```
make O=out ARCH=arm64 LLVM=1 \
     CROSS_COMPILE=aarch64-linux-gnu- CROSS_COMPILE_ARM32=arm-linux-gnueabi- \
     vendor/tb9707f_defconfig
make O=out ARCH=arm64 LLVM=1 \
     CROSS_COMPILE=aarch64-linux-gnu- CROSS_COMPILE_ARM32=arm-linux-gnueabi- \
     Image Image.gz dtbs -j$(nproc)
```

`CROSS_COMPILE*` 不能省：本树的 `LLVM=1` 分支仍用它推导 `--target=` 与 binutils 前缀。

**不要加 `LLVM_IAS=1`**：`arch/arm64/include/asm/atomic_lse.h` 的 `.arch_extension lse` 与
`ALTERNATIVE` 的 `.org` 只有 GNU as 能处理，clang IAS 会报 `instruction requires: lse` /
`invalid .org offset`。原厂也是 clang + GNU as(2.27)。

另：`Makefile` 里原来无条件把 `CC` 包成 `scripts/gcc-wrapper.py`（把所有 warning 当 error，且脚本是
python2 语法、`REAL_CC` 在 `LLVM=1` 下不存在）。已改为 `TB9707F_WARN_WRAPPER=1` 才启用，默认直连 clang，
否则 `make defconfig` 阶段 Kconfig 的 `cc-option` 就会炸在 `SyntaxError` 上。
