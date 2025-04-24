# XCTraceRunner

[中文文档](./README.md)


---

# A Simple Native iOS Performance File (.trace) Parsing Tool

## Environment Requirements

Xcode 12.0.1 + Python 3.7

### Visualization

- To generate HTML, you need to install the packages listed in `requirements.txt`.
- To generate images, you need to download [chromedriver](https://sites.google.com/a/chromium.org/chromedriver/downloads).

## How to Use

Simply run the script, and it will output the corresponding application performance data (FPS + CPU + memory) in JSON format. You can use `python xctrace_parser.py -h` to get help information.

## Technical Principles

Starting from Xcode 12, `xctrace` introduced the `export` program, which allows exporting Instruments-recorded `trace` files in XML format.

To optimize performance, the `export` program does not export all data completely; developers need to parse the XML themselves and make multiple calls to the `export` program to obtain the desired data.

## Covered Instruments

Since each instrument records different data, this tool only parses the following recorded data on the left side and outputs the corresponding data on the right side:

- `Core Animation FPS` => fps
- `Activity Monitor` => cpu, mem, resident size

## About Memory Metrics

Through extensive research, we've deduced the approximate meanings of the various memory values obtained from `sysmon-process` (sourced from Activity Monitor) as follows:

```txt
Memory == VSS
Anonymous Mem == Dirty?
Compressed Mem == Memory compression technology introduced after iOS 7
Purgeable Mem == Clean?
Real Private Mem == USS
Real Shared Mem == USS + shared library memory
Resident Size == RSS
Actual Memory Usage == Dirty + Compressed + Clean. It has been observed that this value is greater than VSS (why?).
```

After actual comparisons, we can conclude that the `Memory` and `RealMemory` metrics in PerfDog correspond to `VSS` and `RSS`, respectively. These two types of memory are extracted, and you can modify the usage as needed.

## Why Create This

The [XCTraceRunner](https://github.com/KuthorX/XCTraceRunner) tool requires recording before triggering the analysis, but often we already have `.trace` files and just don’t know how to analyze them.

## Conclusion

This script simply uses Apple's official `export` tool.

## Main References

```txt
https://github.com/KuthorX/XCTraceRunner
```

--- 
