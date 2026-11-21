# kernel_lenovo_tb9707f

**Lenovo Legion Y700 (TB-9707F) 内核移植 —— 基于联想小新 Pad Pro 12.6 (TB-Q706F) 开源 4.19 源码**

把 [stoicocimihaita/android_kernel_lenovo_sm8250](https://github.com/stoicocimihaita/android_kernel_lenovo_sm8250)
（`TB-Q706F`，骁龙 870 / SM8250 / kona，Linux 4.19.157）移植到 **拯救者 Y700 一代（`TB-9707F`）**，
并附带一套 GitHub Actions 云端编译 + AnyKernel3 自动打包流水线。

> 基底提交：`93058f3a4 arm64: configs: q706f: enable PM_AUTOSLEEP for repowerd`（分支 `halium-11.0`，
> 该分支是本仓库中唯一带 `q706f` 设备支持的）。

---

## 当前状态

| 能力 | 状态 | 说明 |
|---|---|---|
| 云端编译 / 打包 | ✅ 流水线就绪 | `Image` / `Image.gz` / `.config` / `AnyKernel3-*.zip` 自动上传 |
| 开机 | ⚠️ 待实机验证 | 设备树沿用原厂，仅替换内核与 DTB |
| 屏幕 | ⚠️ 预期可用 | 面板节点在 **dtbo**（Novatek NT36523，2560×1600@120Hz），刷机不改 dtbo |
| 触控 | ❌ 暂不可用 | 原厂为 `NVT-ts` **SPI** + HostDL，本树只有 I2C 版 `nt36xxx`，需补驱动 |
| Wi-Fi / 蓝牙 | ⚠️ 依赖 vermagic | 已用 `.scmversion` 钉死 `4.19.157-perf+`，原厂 `.ko` 可加载 |
| 振动 / 游戏拨键 / USB redriver | ❌ 缺驱动 | 联想私有 `CONFIG_*`，源码未公开 |
| KernelSU | ✅ 可选 | `workflow_dispatch` 勾选 `use_kernelsu`（v0.9.5，kprobe） |

详细证据链、缺失符号清单与风险分析见 **[prebuilt/tb9707f/PORTING_NOTES.md](prebuilt/tb9707f/PORTING_NOTES.md)**。

---

## 编译（云端）

推送到 `tb9707f` / `main` / `master` 会触发 `.github/workflows/build_tb9707f.yml`；
也可以在 **Actions → build-tb9707f → Run workflow** 手动触发，并勾选是否集成 KernelSU。

流水线做的事：

1. 安装依赖（含 `aarch64-linux-gnu-` / `arm-linux-gnueabi-` 交叉工具链）；
2. 拉取 **AOSP clang-r416183b**（Googlesource 不可达时自动回退到 LineageOS 预编译镜像），并启用 ccache；
3. 写入 `.scmversion`（内容为单个 `+`）固定 vermagic；
4. `make O=out ARCH=arm64 LLVM=1 LLVM_IAS=1 ... vendor/tb9707f_defconfig`
5. `make ... Image Image.gz dtbs -j$(nproc)`
6. 断言 `kernel.release == 4.19.157-perf+` 且 `vmlinux` 内 vermagic 一致，否则直接失败；
7. 组装 AnyKernel3 刷机包（`Image.gz` + 原厂 `dtb`，`anykernel.sh` 针对 `TB-9707F`）；
8. 上传产物。

产物（Actions 页面下载）：

```
Image
Image.gz
.config
build.log
AnyKernel3-TB9707F-<日期>-<sha>[-KernelSU].zip
```

## 刷机

> **先备份**：`dd if=/dev/block/by-name/boot$(getprop ro.boot.slot_suffix) of=/sdcard/boot_backup.img`
> （本机为 A/B 设备，当前槽位 `_a`；出错可把备份写回同一分区救砖。）

1. 用 TWRP 或任意内核管理器刷入 `AnyKernel3-TB9707F-*.zip`；
2. 脚本只替换 **boot 分区**里的 kernel 与 DTB，**不会写 dtbo**，也不会改动 ramdisk；
3. 刷完 **root 会失效**（APatch/Magisk 的补丁在旧内核里），需要用对应工具重新 patch 一次；
4. 首次开机较慢，若黑屏请回到 recovery 刷回备份的 boot。

## 目录

```
arch/arm64/configs/vendor/tb9707f_defconfig   由真机 /proc/config.gz 静态清洗生成
prebuilt/tb9707f/dtb                          原厂 kona 基础 DTB（与 boot 内逐字节一致）
prebuilt/tb9707f/boot_info.env                cmdline / pagesize / base / offset / os_version / vermagic
prebuilt/tb9707f/anykernel.sh                 TB-9707F 专用打包脚本
prebuilt/tb9707f/PORTING_NOTES.md             移植笔记：硬件、缺失符号、风险
tools/tb9707f/kconfig_filter.py               defconfig 生成器（扫描全树 Kconfig）
.github/workflows/build_tb9707f.yml           云端编译流水线
```

## 几个关键设计

**为什么用原厂 DTB，而不是从源码编？**
`arch/arm64/boot/dts/vendor` 是指向 `vendor/qcom/proprietary/devicetree-4.19` 的悬空符号链接，
联想未公开该目录，`make dtbs` 产出为空。屏幕/触控/充电的节点实际在 **dtbo 分区**，因此刷机时
必须保持 dtbo 原样，同时把 boot 内的基础 DTB 原样带上。

**为什么要钉 `.scmversion`？**
原厂模块的 vermagic 是 `4.19.157-perf+`，那个 `+` 由 `scripts/setlocalversion` 在 git 工作树不干净时追加。
云端注入 KernelSU 会弄脏工作树，导致 `perf++`，Wi-Fi 模块随即拒绝加载。CI 用 `.scmversion`
（内容仅一个 `+`）绕开 git 判断，并在编译后断言，失败即中断。

**为什么要关 `CONFIG_MODULE_SIG_FORCE`？**
`/vendor/lib/modules/*.ko`（41 个，含 `qca_cld3_qca6390.ko`）由联想私钥签名，自定义内核无法通过校验；
关闭强制校验后它们可以带 taint 正常加载。

## 已知问题 / 路线图

- [ ] **触控**：为 `drivers/input/touchscreen/nt36xxx/` 增加 SPI 传输（`novatek,NVT-ts-spi`）与 HostDL 固件下载
- [ ] 振动（`AW8697_HAPTIC`）、游戏拨键（`GAME_MODE_SWITCHER`）、USB redriver 驱动缺失
- [ ] 首次云端构建需实机验证（显示、Wi-Fi、音频）
- [ ] 视需要把 `dtbs` 从流水线移除或补上 `devicetree-4.19`

## 来源与许可

- 内核源码：Lenovo `android_kernel_lenovo_sm8250`（GPL-2.0），本仓库为其派生；
- 打包脚本：AnyKernel3（osm0sis，GPL-3.0）；
- `prebuilt/tb9707f/*` 中的元数据采集自本人持有的设备，仅包含启动参数与设备树，
  用于兼容原厂固件，不含联想私有代码。
