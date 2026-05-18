# Submodule + Patch 复刻流程

本文档说明当前项目如何使用 `git submodule` 管理第三方源码，并用 `patches/vendor/*.patch` 保存本项目需要的适配改动。

核心原则：

- 父仓库只记录第三方仓库的 commit 指针，不直接保存第三方源码文件。
- 本项目对第三方代码的改动保存为 patch，由脚本统一应用。
- 构建产物放在父仓库忽略目录中，避免污染 submodule 工作树。

## 当前第三方依赖

当前项目使用以下 submodule：

```text
src/livox_ros_driver2
src/FAST_LIO_ROS2
third_party/Livox-SDK2
```

对应 patch：

```text
patches/vendor/livox_ros_driver2.patch
patches/vendor/fast_lio_ros2.patch
patches/vendor/livox_sdk2.patch
```

统一应用入口：

```bash
./scripts/apply_vendor_patches.sh
```

## 新环境复刻流程

从干净环境拉取项目后，按顺序执行：

```bash
git submodule update --init --recursive
./scripts/apply_vendor_patches.sh
./scripts/build_livox_sdk2.sh
env ROS_LOG_DIR=/tmp/ros_log ./scripts/with_venv.sh colcon build \
  --packages-select livox_ros_driver2 fast_lio nav_mapping uav_bringup \
  --symlink-install
```

其中：

- `git submodule update --init --recursive` 拉取第三方源码到指定 commit。
- `./scripts/apply_vendor_patches.sh` 把本项目适配改动应用到第三方源码。
- `./scripts/build_livox_sdk2.sh` 把 Livox-SDK2 安装到 `.deps/livox_sdk2`。
- `./scripts/with_venv.sh ...` 保证 ROS 构建使用项目虚拟环境。

验证：

```bash
./scripts/apply_vendor_patches.sh
git ls-files --stage src/livox_ros_driver2 src/FAST_LIO_ROS2 third_party/Livox-SDK2
git status --short
```

预期结果：

- 第二次运行 `apply_vendor_patches.sh` 应显示 `Already applied ...`。
- `git ls-files --stage` 中三个第三方路径应是 `160000` 类型。
- `git status --short` 里 submodule 可能显示小写 `m`，表示本地 patch 已应用到 submodule 工作树，这是正常现象。

## 日常使用规则

可以暂存 submodule 指针，但不要把第三方源码作为普通文件加入父仓库：

```bash
git add src/livox_ros_driver2 src/FAST_LIO_ROS2 third_party/Livox-SDK2
```

上面这个命令只应暂存 submodule 指针，不应出现大量第三方文件。

检查父仓库是否仍然只记录 gitlink：

```bash
git ls-files --stage src/livox_ros_driver2 src/FAST_LIO_ROS2 third_party/Livox-SDK2
```

正确形式类似：

```text
160000 <commit> 0 src/livox_ros_driver2
160000 <commit> 0 src/FAST_LIO_ROS2
160000 <commit> 0 third_party/Livox-SDK2
```

检查暂存内容是否异常：

```bash
git diff --cached --stat
```

如果看到成千上万行第三方源码进入暂存区，说明误把 submodule 转成普通目录或误加了 vendor 源码，需要先停下来处理。

## 修改第三方适配的流程

以 `src/livox_ros_driver2` 为例：

1. 在 submodule 内直接修改需要适配的文件。

2. 确认改动范围：

```bash
git -C src/livox_ros_driver2 diff
```

3. 如果适配新增了文件，先把新增文件标记为 intent-to-add，让 `git diff` 能包含它：

```bash
git -C src/livox_ros_driver2 add -N package.xml
```

4. 生成或更新 patch：

```bash
git -C src/livox_ros_driver2 diff --binary > patches/vendor/livox_ros_driver2.patch
```

5. 验证 patch 可重复应用。先在 submodule 内撤回 patch，再通过统一脚本应用：

```bash
git -C src/livox_ros_driver2 apply --reverse ../../patches/vendor/livox_ros_driver2.patch
./scripts/apply_vendor_patches.sh
./scripts/apply_vendor_patches.sh
```

第二次执行脚本应显示 `Already applied patches/vendor/livox_ros_driver2.patch`。

6. 暂存父仓库中的 patch 和脚本改动：

```bash
git add patches/vendor/livox_ros_driver2.patch scripts/apply_vendor_patches.sh
```

如果只是修改 patch，不要在第三方 submodule 内提交 commit；父仓库靠 patch 复刻这部分改动。

## 新增第三方 submodule 的流程

示例：

```bash
git submodule add <repo-url> <path>
git -C <path> checkout <commit-or-branch>
```

然后：

1. 在 `<path>` 内完成本项目需要的适配。
2. 如果有新增文件，先标记为 intent-to-add：

```bash
git -C <path> add -N <new-file>
```

3. 生成 patch：

```bash
git -C <path> diff --binary > patches/vendor/<name>.patch
```

4. 在 `scripts/apply_vendor_patches.sh` 追加：

```bash
apply_patch_if_needed "<path>" "patches/vendor/<name>.patch"
```

5. 暂存父仓库文件：

```bash
git add .gitmodules <path> patches/vendor/<name>.patch scripts/apply_vendor_patches.sh
```

6. 检查 `<path>` 在父仓库中是 `160000`：

```bash
git ls-files --stage <path>
```

## 更新上游版本的流程

如果需要把某个 submodule 更新到上游新版本：

```bash
git -C <path> fetch --all --tags
git -C <path> checkout <new-commit>
./scripts/apply_vendor_patches.sh
```

如果 patch 冲突：

1. 查看冲突原因：

```bash
git -C <path> diff
```

2. 在 submodule 内手工调整代码。
3. 如果有新增文件，先标记为 intent-to-add：

```bash
git -C <path> add -N <new-file>
```

4. 重新生成 patch：

```bash
git -C <path> diff --binary > patches/vendor/<name>.patch
```

5. 暂存父仓库的 submodule 指针和 patch：

```bash
git add <path> patches/vendor/<name>.patch
```

## 清理与恢复

如果 submodule 工作树被构建产物污染，优先清理构建脚本输出目录，而不是删除源码。当前项目的 Livox-SDK2 构建输出在：

```text
.deps/build/livox_sdk2
.deps/livox_sdk2
```

如果需要恢复某个 submodule 到父仓库记录的干净 commit：

```bash
git submodule update --init --recursive --force <path>
./scripts/apply_vendor_patches.sh
```

注意：这个命令会覆盖 `<path>` 内未保存的本地改动。执行前先用下面命令确认：

```bash
git -C <path> status --short
git -C <path> diff
```

## 提交前检查清单

提交前执行：

```bash
git status --short
git diff --cached --stat
git ls-files --stage src/livox_ros_driver2 src/FAST_LIO_ROS2 third_party/Livox-SDK2
./scripts/apply_vendor_patches.sh
```

确认：

- 第三方路径在父仓库中仍是 `160000`。
- `patches/vendor/*.patch` 能表达所有第三方适配改动。
- 构建产物没有进入暂存区。
- `apply_vendor_patches.sh` 可重复执行。

## 与 MID360 接入的关系

MID360 + FAST-LIO2 的功能说明见：

```text
docs/MID360_FAST_LIO2_INTEGRATION.md
```

本文件只说明源码复刻和第三方 patch 维护流程。
