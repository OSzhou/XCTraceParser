# XCTraceParser

[English README](./README_en.md)

一个简单的原生 iOS 性能文件(.trace)解析工具。

## 环境要求

XCode 12.0.1 + python 3.7

### 可视化

- 生成 html，需要安装 [requirements.txt](./requirements.txt) 下的包

- 生成图片，需要下载 [chromedriver](https://sites.google.com/a/chromium.org/chromedriver/downloads)

## 如何使用

直接运行该脚本即可，最后会输出对应应用的性能数据（fps + cpu + mem）的 Json 。
可用 `python xctrace_parser.py -h` 获取帮助信息。

## 技术原理

XCode 12 以后， `xctrace` 新增了 `export` 程序，可以将 Instruments 录制的 `trace` 文件以 XML 形式导出。

可能是考虑到性能， `export` 导出时并没有完全将所有数据导出，需要开发者自行解析 XML ，并通过多次调用 `export` 程序，得到预期数据。

## 覆盖的 Instruments

由于每个 instrument 录制的数据都不一样，这里仅解析以下 => 左侧的录制数据，最终输出保存 => 右侧的数据：

- `Core Animation FPS` => fps
- `Activity Monitor` => cpu、mem、resident size

## 关于内存指标

通过半天搜集资料研究，基本可以得出 `sysmon-process`（从 Activity Monitor 获取） 的各个内存值大致含义如下

```txt
Memory == VSS
Anonymous Mem == Dirty？
Compressed Mem == iOS 7 之后的压缩内存技术
Purgeable Mem == Clean？
Real Private Mem == USS
Real Shared Mem == USS + 共享库内存
Resident Size == RSS
APP 实际使用内存 == Dirty + Compressed + Clean，实际计算发现比 VSS 大（为什么？）
```

经过实际比对，可得出 PerfDog 的 `Memory`、`RealMemory` 即为 `VSS`、`RSS`，故先提取这两种内存，有需要可自行修改使用 @_@

## 为什么做这个

[XCTraceRunner](https://github.com/KuthorX/XCTraceRunner) 工具需要录制后再触发分析，很多时候我们是已经有.trace文件，只是不知道如何分析。

## 总结

这个脚本只是简单地使用了苹果官方提供的 `export` 而已。

## 主要参考资料

```txt
https://github.com/KuthorX/XCTraceRunner
```
