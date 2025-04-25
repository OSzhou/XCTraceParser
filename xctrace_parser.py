import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import argparse
import json
from data_visualizer import ParsedData, DataVisualizer
import time
import random

def main():
    # 确保临时目录存在
    temp_dirs = ["./temp/parse", "./temp/save", "./temp/visualize"]
    for d in temp_dirs:
        Path(d).mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser(description="XCTrace File Parser and Visualizer")
    parser.add_argument(
        "-trace_path",
        required=True,
        help="Path to .trace file to analyze",
    )
    parser.add_argument(
        "-target_process_name",
        required=True,
        help="Target process name to analyze (e.g. Steam)",
    )
    args = parser.parse_args()

    # 生成唯一ID（基于时间戳+随机数）
    trace_id = f"{int(time.time())}_{random.randint(1000,9999)}"

    # 解析流程
    log_path = f"./temp/parse/{trace_id}_parse.log"
    parser = XCTraceParser(
        trace_path=args.trace_path,
        log_path=log_path,
        target_process_name=args.target_process_name,
        trace_id=trace_id
    )
    parser.parse()
    parser.save()

    # 可视化流程
    print("开始可视化 Start visualize")
    html_path = f"./temp/visualize/{trace_id}_report.html"
    
    # 转换数据格式
    fps_data = XCTraceVisualizer(
        title="FPS Data",
        trace_id=trace_id,
        data_type=DataType.FPS,
        data_detail=parser.fps_values
    ).transform_data()

    cpu_data = XCTraceVisualizer(
        title="CPU Usage",
        trace_id=trace_id,
        data_type=DataType.CPU,
        data_detail=parser.cpu_values
    ).transform_data()

    mem_data = XCTraceVisualizer(
        title="Memory Usage",
        trace_id=trace_id,
        data_type=DataType.MEM,
        data_detail=parser.mem_values
    ).transform_data()

    # 生成可视化报告
    dv = DataVisualizer(html_path=html_path)
    dv.add_parsed_data(fps_data)
    dv.add_parsed_data(cpu_data)
    dv.add_parsed_data(mem_data)
    dv.render_html()
    
    print(f"可视化完成 Report saved to: {html_path}")

class XCTraceParser:
    def __init__(self, trace_path, log_path, target_process_name, trace_id=None):
        self.trace_path = trace_path
        self.log_path = log_path
        self.target_process_name = target_process_name
        self.trace_id = trace_id or self._generate_trace_id()
        
        # 路径配置
        self.temp_path = "./temp/parse"
        self.prefix_cmd = f'xcrun xctrace export --input "{self.trace_path}"'
        
        # 数据存储
        self.fps_values = None
        self.cpu_values = None
        self.mem_values = None

    def _generate_trace_id(self):
        return f"{int(time.time())}_{random.randint(1000, 9999)}"

    def print_log(self, message):
        log_line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        print(log_line)
        with open(self.log_path, "a") as f:
            f.write(log_line + "\n")

    def parse(self):
        self.print_log("启动解析进程 Starting trace parsing")
        
        try:
            self._export_toc()
            self._parse_fps()
            self._parse_cpu_mem()
            
            # 反转时间序列（原始数据为倒序）
            self.fps_values = list(reversed(self.fps_values))
            self.cpu_values = list(reversed(self.cpu_values))
            self.mem_values = list(reversed(self.mem_values))
            
            self.print_log("解析成功完成 Parsing completed successfully")
        except Exception as e:
            self.print_log(f"解析失败! 错误信息: {str(e)}")
            raise

    def save(self, output_dir="./temp/save"):
        Path(output_dir).mkdir(exist_ok=True)
        
        def _save(data, suffix):
            filename = f"{self.trace_id}_{suffix}.json"
            path = os.path.join(output_dir, filename)
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            self.print_log(f"保存文件: {path}")

        _save(self.fps_values, "fps")
        _save(self.cpu_values, "cpu")
        _save(self.mem_values, "mem")

    def _export_xml(self, schema_name, output_suffix):
        """通用XML导出方法"""
        output_path = os.path.join(self.temp_path, f"{self.trace_id}_{output_suffix}.xml")
        cmd = (
            f"{self.prefix_cmd} "
            f"--output {output_path} "
            f"--xpath '/trace-toc/run[@number=\"1\"]/data/table[@schema=\"{schema_name}\"]'"
        )
        self.print_log(f"执行命令: {cmd}")
        exit_code = os.system(cmd)
        if exit_code != 0:
            raise RuntimeError(f"命令执行失败，退出码: {exit_code}")
        return output_path

    def _export_toc(self):
        """导出目录结构"""
        output_path = os.path.join(self.temp_path, f"{self.trace_id}_toc.xml")
        cmd = f"{self.prefix_cmd} --output {output_path} --toc"
        self.print_log(f"导出目录结构: {cmd}")
        os.system(cmd)

    def _parse_fps(self):
        """解析FPS数据"""
        xml_path = self._export_xml(
            schema_name="core-animation-fps-estimate",
            output_suffix="core-animation-fps"
        )
        
        self.print_log(f"解析FPS数据: {xml_path}")
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        fps_data = []
        cache = {}
        for row in root.findall(".//row"):
            time_ele = self._get_cached_element(row, ".//start-time", cache)
            fps_ele = self._get_cached_element(row, ".//fps", cache)
            
            fps_data.append({
                "time": time_ele.attrib["fmt"],
                "fps": float(fps_ele.text)
            })
        
        self.fps_values = fps_data
        self.print_log(f"获取到 {len(fps_data)} 条FPS记录")

    def _parse_cpu_mem(self):
        """解析CPU和内存数据"""
        xml_path = self._export_xml(
            schema_name="sysmon-process",
            output_suffix="sysmon-process"
        )
        
        self.print_log(f"解析CPU/内存数据: {xml_path}")
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        cpu_data = []
        mem_data = []
        cache = {}
        last_cpu = 0.0
        mem_text = None
        resident_text = None
        for row in root.findall(".//row"):
            # 预加载所有 size-in-bytes 元素到缓存
            for size_ele in row.findall(".//size-in-bytes"):
                if "id" in size_ele.attrib:
                    cache[size_ele.attrib["id"]] = size_ele
            # 提取时间戳
            time_ele = self._get_cached_element(row, ".//start-time", cache)
            timestamp = time_ele.attrib["fmt"]
            
            # 检查进程名称
            process_ele = self._get_cached_element(row, ".//process", cache)
            process_name = process_ele.attrib["fmt"].split()[0]
            if process_name != self.target_process_name:
                continue
                
            # 解析CPU
            cpu_ele = self._get_cached_element(row, ".//system-cpu-percent", cache)
            cpu_value = float(cpu_ele.text) if cpu_ele is not None else last_cpu
            last_cpu = cpu_value
            
            # 解析内存
            mem_ele = self._get_cached_element(row, ".//size-in-bytes[3]", cache)
            resident_ele = self._get_cached_element(row, ".//size-in-bytes[9]", cache)
            
            if mem_ele is not None:
                mem_text = mem_ele.text
            else:
                mem_text = "-1"

            if resident_ele is not None:
                resident_text = resident_ele.text
            else:
                resident_text = "-1"

            cpu_data.append({"time": timestamp, "cpu": cpu_value})
            mem_data.append({
                "time": timestamp,
                "memory": float(mem_text) / 1048576,  # 转换为MB
                "resident_size": float(resident_text) / 1048576
            })
        
        self.cpu_values = cpu_data
        self.mem_values = mem_data
        self.print_log(f"获取到 {len(cpu_data)} 条CPU记录和 {len(mem_data)} 条内存记录")

    def _get_cached_element(self, row, xpath, cache):
        """
        处理XML压缩结构
        :param row: XML行元素
        :param xpath: 查找路径
        :param cache: ID缓存字典
        :return: 第一个匹配的元素
        """
        elements = row.findall(xpath)
        if not elements:
            return None
            
        first_element = None
        for ele in elements:
             # 处理引用逻辑
            if "ref" in ele.attrib:
                ref_id = ele.attrib["ref"]
                if ref_id not in cache:
                    self.print_log(f"严重警告: 跨行引用 {ref_id} 未找到，请检查XML结构！")
                    continue
                ele = cache[ref_id]

            # 处理id逻辑
            if "id" in ele.attrib:
                cache[ele.attrib["id"]] = ele

            # 记录第一个有效元素
            if first_element is None:
                first_element = ele
            # attrib = ele.attrib
            # if attrib.get("id"):
            #     cache[attrib["id"]] = ele
            # else:
            #     ele = cache[attrib["ref"]]
            # if not first_element:
            #     first_element = ele
        return first_element

# 保留原有DataType枚举和可视化类
class DataType:
    FPS = 0
    CPU = 1
    MEM = 2


def date2timestamp(date_str, format_str="%M:%S"):
    import time

    tss1 = date_str
    time_array = time.strptime(tss1, format_str)
    return int(time.mktime(time_array))


def timestamp2date(timestamp, format_str="%H:%M:%S"):
    import time

    time_array = time.localtime(timestamp)
    date = time.strftime(format_str, time_array)
    return date

def seconds_to_hms(seconds):
    """将总秒数转换为 HH:MM:SS 格式"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def duration_to_seconds(duration_str):
    """
    将时长字符串转换为总秒数
    支持格式:
    - SS (秒)
    - MM:SS (分:秒)
    - HH:MM:SS (时:分:秒)
    """
    # print(f"duration_str:{duration_str}")
    # parts = list(map(float, duration_str.split('.')))  # 分割整数和小数部分
    # time_part = parts[0]
    # sub_seconds = parts[1] if len(parts) > 1 else 0

    # 分割时、分、秒
    segments = list(map(int, str(duration_str).split(':')))
    segments.reverse()  # 从秒开始处理

    seconds = 0
    multipliers = [1, 60, 3600]  # 秒、分、时的倍数
    for i, val in enumerate(segments):
        seconds += val * multipliers[i]
    # if seconds > 3600:
    #     return 3600
    return seconds



class XCTraceVisualizer:
    def __init__(self, title, trace_id, data_type: DataType, data_detail: list):
        self.title = title
        self.trace_id = trace_id
        self.data_type = data_type
        self.data_detail = data_detail

        self._y_label = None
        # list, {"time": "MM:SS", "value": number}
        self._t_data = None
        # print(f"list data: {data_detail}")

    def transform_data(self):
        t = self.data_type
        if t == DataType.FPS:
            self._y_label = "FPS"
            self._t_data = self._transform_fps_data()
        elif t == DataType.CPU:
            self._y_label = "CPU"
            self._t_data = self._transform_cpu_data()
        elif t == DataType.MEM:
            self._y_label = "MEM"
            self._t_data = self._transform_mem_data()
        return self._get_dv_parsed_data()

    def _get_dv_parsed_data(self):
        y_seq = []
        x_seq = []
        for item in self._t_data:
            y_seq.append(item["value"])
            x_seq.append(item["time"])
        return ParsedData(
            title=self.title, y_label=self._y_label, y_seq=y_seq, x_seq=x_seq
        )

    def _transform_fps_data(self):
        d = []
        for item in self.data_detail:
            _time = item["time"]
            _value = item["fps"]
            # ts = date2timestamp(_time.split(".")[0])
            # 使用新函数计算总秒数
            ts = duration_to_seconds(_time.split(".")[0])
            d.append({"time": ts, "value": _value})
        s_data = sorted(d, key=lambda item: item["time"])
        return self._remove_same_time_data(s_data)

    def _transform_cpu_data(self):
        d = []
        for item in self.data_detail:
            _time = item["time"]
            _value = round(item["cpu"], 2)
            # ts = date2timestamp(_time.split(".")[0])
            # 使用新函数计算总秒数
            ts = duration_to_seconds(_time.split(".")[0])
            d.append({"time": ts, "value": _value})
        s_data = sorted(d, key=lambda item: item["time"])
        return self._remove_same_time_data(s_data)

    def _transform_mem_data(self):
        d = []
        for item in self.data_detail:
            _time = item["time"]
            _value = round(item["memory"], 2)
            # ts = date2timestamp(_time.split(".")[0])
            # 使用新函数计算总秒数
            ts = duration_to_seconds(_time.split(".")[0])
            d.append({"time": ts, "value": _value})
        s_data = sorted(d, key=lambda item: item["time"])
        return self._remove_same_time_data(s_data)

    def _remove_same_time_data(self, data):
        filter_data = []
        before_item = None
        for item in data:
            _time = item["time"]
            _value = item["value"]
            # _date = timestamp2date(item["time"])
            _date = seconds_to_hms(_time)
            if before_item:
                if before_item["time"] == _time:
                    filter_data[-1]["value"] = _value
                else:
                    filter_data.append({"time": _date, "value": _value})
            else:
                filter_data.append({"time": _date, "value": _value})
            before_item = item
        return filter_data


def get_random_id(length=8, seed="1234567890qwertyuiopasdfghjklzxcvbnm"):
    import random

    result = ""
    for _ in range(length):
        result += random.choice(seed)
    return result



if __name__ == "__main__":
    main()
