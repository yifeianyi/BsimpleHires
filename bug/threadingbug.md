[WorkPage] 转换任务已成功启动
[工作线程] 开始执行转换任务
[工作线程] 输入文件数量: 3
[工作线程] 输出目录: E:/Project/PyQt/BsimpleHiresTransverter/test/output
[工作线程] 线程状态设置为运行中
[工作线程] 检查ffmpeg可用性...
[工作线程] ffmpeg检查通过
[工作线程] 创建输出目录...
[工作线程] 输出目录已确保存在: E:/Project/PyQt/BsimpleHiresTransverter/test/output
[工作线程] 开始执行多线程批量转换，最大并发数: 2
[工作线程] 异常: 转换过程中出现错误: name 'threading' is not defined
[工作线程] 异常详情: Traceback (most recent call last):
  File "E:\Project\PyQt\BsimpleHiresTransverter\workers\conversion_worker.py", line 60, in run
    stop_event=threading.Event(),  # 创建停止事件
               ^^^^^^^^^
NameError: name 'threading' is not defined. Did you forget to import 'threading'

[WorkPage] 转换错误回调: 转换过程中出现错误: name 'threading' is not defined