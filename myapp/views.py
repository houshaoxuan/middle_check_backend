from django.shortcuts import render
from django.http import JsonResponse
from django.http import StreamingHttpResponse
import subprocess
import time
import os

# 定义模拟延迟时间
INITIAL_DELAY_SECONDS = 8.0  # 第一次输出前的预处理时间 (例如 3秒)
RUN_PHASE_DELAY_SECONDS = 0.1 # 核心运行阶段每行输出的间隔 (例如 50毫秒)

def index(request):
    return render(request, 'myapp/index.html')

def api_echo(request):
    msg = request.GET.get('msg', '')
    return JsonResponse({'message': msg})

def run(request):
    algorithm = request.GET.get('alogrithm')
    dataset = request.GET.get('dataset')

    if algorithm == 'bfs':
        # 启动 bfs 可执行文件
        process = subprocess.Popen(
            ['D:/Python/powerG/bfs.exe', algorithm, dataset],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
    elif algorithm == 'sssp':
        # 启动 C++ 可执行文件
        process = subprocess.Popen(
            ['D:/Python/powerG/sssp.exe', algorithm, dataset],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

    # 生成器，逐行读取 C++ 输出
    def stream():
        for line in iter(process.stdout.readline, ''):
            yield line  # 每一行立即发送给前端
        process.stdout.close()
        process.wait()

    # 流式返回，content_type 设置为 text/plain 或 application/octet-stream
    return StreamingHttpResponse(stream(), content_type='text/plain')

def runTest(request):
    # 注意：修正了查询参数名拼写错误 'alogrithm' -> 'algorithm'
    algorithm = request.GET.get('algorithm')
    dataset = request.GET.get('dataset')
    def stream_sse():
        if not algorithm or not dataset:
             yield format_sse("[error]")
             return

        lines = [
            f"Starting algorithm: {algorithm}",
            f"Processing dataset: {dataset}",
            "Step 1 completed",
            "Step 2 completed",
            "Step 3 completed",
            "bfs median_TEPS:                     4.3966e+12"
        ]

        try:
            for line in lines:
                # 实时发送日志到客户端
                yield format_sse(line)
                time.sleep(0.5)

            # 成功完成，发送约定好的 [done] 标记
            yield format_sse("[done]")

        except Exception:
            # 捕获异常，发送错误标记
            yield format_sse("[error]:Exception")

    # 必须使用 'text/event-stream' Content-Type
    response = StreamingHttpResponse(
        stream_sse(),
        content_type='text/event-stream'
    )
    # 禁用缓存是 SSE 的标准做法
    response['Cache-Control'] = 'no-cache'

    # 允许跨域（如果需要）
    response['Access-Control-Allow-Origin'] = '*'

    return response

# --- 辅助函数：格式化 SSE 消息 ---
def format_sse(data: str) -> str:
    """将数据格式化为 SSE 协议要求的字符串"""
    # data: [内容]
    # \n\n (必须用两个换行符结束)
    return f"data: {data}\n\n"

def stream_sse_simulated_timing(FILE_PATH):
    # 标志位：用于区分是初始化阶段还是核心运行阶段
    is_running_phase = False

    # 记录是否是第一次输出，以便应用长延迟
    is_first_output = True

    # 用于识别核心运行阶段开始的关键词
    RUN_START_KEYWORD = "source:"

    try:
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue # 跳过空行

                # 检查是否进入核心运行阶段
                if line.startswith(RUN_START_KEYWORD):
                    is_running_phase = True

                # --- 应用延迟逻辑 ---

                if not is_running_phase:
                    # 阶段 1: 预处理/初始化阶段
                    if is_first_output:
                        # 仅在第一行输出前应用一次长延迟
                        time.sleep(INITIAL_DELAY_SECONDS)
                        is_first_output = False

                    # 预处理阶段的日志输出应该较快（因为文件中的 WARNING/INFO 通常是连续输出）
                    # 我们可以不加延迟，让它迅速输出直到遇到核心运行阶段的标记
                    pass # 不加延迟或使用极短延迟

                elif is_running_phase:
                    # 阶段 2: 核心运行阶段 (遇到 'source:' 之后的行)
                    time.sleep(RUN_PHASE_DELAY_SECONDS)

                # 阶段 3: 结果汇总阶段 (文件读取完后自动处理，无需特殊延迟)

                # 实时将文件内容作为日志发送给客户端
                yield format_sse(line)

        # 3. 文件读取成功，发送 [done] 标记
        yield format_sse("[done]")

    except FileNotFoundError:
        yield format_sse("[error] Result file not found.")
    except Exception as e:
        yield format_sse(f"[error] Failed to read file: {str(e)}")

# --- 视图函数：读取文件并建立SSE流 ---
def readResult_via_sse(request):
    # 注意：修正了查询参数名拼写错误 'alogrithm' -> 'algorithm'
    algorithm = request.GET.get('algorithm')
    dataset = request.GET.get('dataset')

    # 假设结果文件放在项目根目录下的 'results' 文件夹中
    # 并且文件名格式为：<algorithm>_<dataset>.txt
    RESULTS_DIR = os.path.join(os.getcwd(), 'results')

    # 动态构建结果文件的路径
    if algorithm and dataset:
        FILE_NAME = f"{algorithm}_{dataset}.txt"
        FILE_PATH = os.path.join(RESULTS_DIR, FILE_NAME)
    else:
        # 如果参数缺失，FILE_PATH 可能不会被使用，但我们先定义它
        FILE_PATH = None

    def stream_sse():
        # 1. 参数校验
        if not algorithm or not dataset:
            yield format_sse("[error] Missing algorithm or dataset.")
            return

        yield format_sse(f"Attempting to read results from: {FILE_PATH}")

        # 2. 读取文件并流式返回内容
        try:
            yield from stream_sse_simulated_timing(FILE_PATH)

            # 3. 文件读取成功，发送 [done] 标记
            yield format_sse("[done]")

        except FileNotFoundError:
            # 捕获文件找不到的错误
            error_msg = f"[error] Result file not found: {FILE_PATH}"
            yield format_sse(error_msg)
        except Exception as e:
            # 捕获其他读取或编码异常
            error_msg = f"[error] Failed to read file: {str(e)}"
            yield format_sse(error_msg)

    # 4. 返回 StreamingHttpResponse
    response = StreamingHttpResponse(
        stream_sse(),
        content_type='text/event-stream'
    )
    # 标准 SSE 响应头配置
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    response['Access-Control-Allow-Origin'] = '*'

    return response