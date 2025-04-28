import os
# import sys
import json
import argparse
from data_visualizer import FMParsedData, DataVisualizer
import time
import random
from pyecharts.charts import Bar, Line, Page

def read_json_files(directory):
    """
    读取指定目录下的所有JSON文件
    :param directory: 要扫描的目录路径
    :return: 包含所有JSON文件数据的字典 {filename: data}
    """
    json_paths = []
    
    # 验证目录存在性
    if not os.path.exists(directory):
        raise FileNotFoundError(f"目录不存在: {directory}")
    
    # 遍历目录
    for root, dirs, files in os.walk(directory):
        for filename in files:
            # 筛选JSON文件
            if filename.lower().endswith('.json'):
                filepath = os.path.join(root, filename)
                json_paths.append(filepath)
                
    return json_paths

def main():
    
    # 创建命令行参数解析器
    # parser = argparse.ArgumentParser(description='Parse multiple JSON files.')
    # parser.add_argument('json_files', type=str, nargs='+', help='The paths to the JSON files to parse.')

    # # 解析命令行参数
    # args = parser.parse_args()

    # 配置命令行参数解析
    parser = argparse.ArgumentParser(
        description='读取指定目录下的所有JSON文件',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        'path',
        type=str,
        help='要扫描的目录路径'
    )
    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help='是否递归扫描子目录'
    )
    args = parser.parse_args()

    results = read_json_files(args.path)
    
    json_parser = FMJsonParser(
        json_files = results
    )
    
    # 可视化流程
    print("开始可视化 Start visualize")
    html_path = f"./temp/visualize/{json_parser.trace_id}_report.html"
    
    # 转换数据格式
    fps_data = XCTraceVisualizer(
        title="FPS Data",
        trace_id=json_parser.trace_id,
        data_type=DataType.FPS,
        data_detail=json_parser.fps_values_dict,
        file_names=json_parser.fps_file_names
    ).transform_data()

    gpu_data = XCTraceVisualizer(
        title="GPU Data",
        trace_id=json_parser.trace_id,
        data_type=DataType.GPU,
        data_detail=json_parser.gpu_values_dict,
        file_names=json_parser.gpu_file_names
    ).transform_data()

    cpu_data = XCTraceVisualizer(
        title="CPU Usage",
        trace_id=json_parser.trace_id,
        data_type=DataType.CPU,
        data_detail=json_parser.cpu_values_dict,
        file_names=json_parser.cpu_file_names
    ).transform_data()

    mem_data = XCTraceVisualizer(
        title="Memory Usage",
        trace_id=json_parser.trace_id,
        data_type=DataType.MEM,
        data_detail=json_parser.mem_values_dict,
        file_names=json_parser.mem_file_names
    ).transform_data()

    # 生成可视化报告
    dv = DataVisualizer(html_path=html_path)
    dv.add_multi_line_parsed_data(fps_data)
    dv.add_multi_line_parsed_data(gpu_data)
    dv.add_multi_line_parsed_data(cpu_data)
    dv.add_multi_line_parsed_data(mem_data)
    dv.render_html()
    
    print(f"可视化完成 Report saved to: {html_path}")

class FMJsonParser:
    def __init__(self, json_files: list):
        
        # 数据存储
        self.fps_values_dict = {}
        self.gpu_values_dict = {}
        self.cpu_values_dict = {}
        self.mem_values_dict = {}

        self.fps_file_names = []
        self.gpu_file_names = []
        self.cpu_file_names = []
        self.mem_file_names = []
        self.trace_id = self._generate_trace_id()
        for json_file_path in json_files:
            # 提取文件名（带扩展名）
            file_name_with_ext = os.path.basename(json_file_path)
        
            # 提取文件名（不带扩展名）
            file_name_without_ext = os.path.splitext(file_name_with_ext)[0]
            key = file_name_without_ext.split('_')[-1]  # 获取元素的后缀关键字
            
            json_list = self._parse_json_file(json_file_path)
            if key == 'fps':
                self.fps_file_names.append(file_name_without_ext)
                self.fps_values_dict[file_name_without_ext] = json_list
            elif key == 'gpu':
                self.gpu_file_names.append(file_name_without_ext)
                self.gpu_values_dict[file_name_without_ext] = json_list
            elif key == 'cpu':
                self.cpu_file_names.append(file_name_without_ext)
                self.cpu_values_dict[file_name_without_ext] = json_list
            elif key == 'mem':
                self.mem_file_names.append(file_name_without_ext)
                self.mem_values_dict[file_name_without_ext] = json_list

    def _generate_trace_id(self):
        return f"{int(time.time())}_{random.randint(1000, 9999)}"

    def _parse_json_file(self, json_file_path):
        # 检查文件是否存在
        if not os.path.isfile(json_file_path):
            print(f"文件 {json_file_path} 不存在.")
        else:
            # 读取并解析 JSON 文件
            with open(json_file_path, 'r') as file:
                try:
                    data = json.load(file)  # 解析 JSON 数据
                    # 输出解析后的数据
                    print(f"\n解析文件: {json_file_path}")
                    return list(reversed(data))
                    
                except json.JSONDecodeError as e:
                    print(f"解析 {json_file_path} 时发生错误:", e)
                    return []


# 保留原有DataType枚举和可视化类
class DataType:
    FPS = 0
    GPU = 1
    CPU = 2
    MEM = 3


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
    def __init__(self, title, trace_id, data_type: DataType, data_detail, file_names: list):
        self.title = title
        self.trace_id = trace_id
        self.data_type = data_type
        # list, {"hetao_1688_mem": {"time": "MM:SS", "value": number}}
        self.data_detail = data_detail
        # list, ["hetao_1688_mem"]
        self.file_names = file_names

        self._y_label = None

    def transform_data(self):
        t = self.data_type
        if t == DataType.FPS:
            self._y_label = "FPS"
            for name in self.file_names:
                tmp_data = self.data_detail[name]
                tmp_t_data = self._transform_fps_data(tmp_data)
                self.data_detail[name] = tmp_t_data
        elif t == DataType.GPU:
            self._y_label = "GPU"
            for name in self.file_names:
                tmp_data = self.data_detail[name]
                tmp_t_data = self._transform_gpu_data(tmp_data)
                self.data_detail[name] = tmp_t_data
        elif t == DataType.CPU:
            self._y_label = "CPU"
            for name in self.file_names:
                tmp_data = self.data_detail[name]
                tmp_t_data = self._transform_cpu_data(tmp_data)
                self.data_detail[name] = tmp_t_data
        elif t == DataType.MEM:
            self._y_label = "MEM"
            for name in self.file_names:
                tmp_data = self.data_detail[name]
                tmp_t_data = self._transform_mem_data(tmp_data)
                self.data_detail[name] = tmp_t_data
        return self._get_dv_parsed_data()

    def _get_dv_parsed_data(self):
        y_dict = {}
        x_seq = []

        self.file_names = sorted(self.file_names)
        for name in self.file_names:
            t_y_seq = []
            t_x_seq = []
            for item in self.data_detail[name]:
                t_y_seq.append(item["value"])
                t_x_seq.append(item["time"])
            if len(t_x_seq) > len(x_seq):
                x_seq = t_x_seq
            y_dict[name] = t_y_seq

        fTitle = self.title
        # if y_seq:
        #     # 获取最大值
        #     max_v= max(y_seq)

        #     # 获取最小值
        #     min_v = min(y_seq)

        #     # 获取平均值
        #     ave_v = sum(y_seq) / len(y_seq)
        #     fTitle = f"{self.title}: max: {max_v} min: {min_v} avg: {round(ave_v, 1)}"

        return FMParsedData(
            title=fTitle, file_names = self.file_names, y_label=self._y_label, y_seq=y_dict, x_seq=x_seq
        )

    def _transform_fps_data(self, data_detail):
        d = []
        for item in data_detail:
            _time = item["time"]
            _value = item["fps"]
            # ts = date2timestamp(_time.split(".")[0])
            # 使用新函数计算总秒数
            ts = duration_to_seconds(_time.split(".")[0])
            d.append({"time": ts, "value": _value})
        s_data = sorted(d, key=lambda item: item["time"])
        return self._remove_same_time_data(s_data)

    def _transform_gpu_data(self, data_detail):
        d = []
        for item in data_detail:
            _time = item["time"]
            _value = item["gpu"]
            # ts = date2timestamp(_time.split(".")[0])
            # 使用新函数计算总秒数
            ts = duration_to_seconds(_time.split(".")[0])
            d.append({"time": ts, "value": _value})
        s_data = sorted(d, key=lambda item: item["time"])
        return self._remove_same_time_data(s_data)

    def _transform_cpu_data(self, data_detail):
        d = []
        for item in data_detail:
            _time = item["time"]
            _value = round(item["cpu"], 2)
            # ts = date2timestamp(_time.split(".")[0])
            # 使用新函数计算总秒数
            ts = duration_to_seconds(_time.split(".")[0])
            d.append({"time": ts, "value": _value})
        s_data = sorted(d, key=lambda item: item["time"])
        return self._remove_same_time_data(s_data)

    def _transform_mem_data(self, data_detail):
        d = []
        for item in data_detail:
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

if __name__ == "__main__":
    main()
