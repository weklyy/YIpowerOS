# core/benchmark.py
import time
import json
import logging
from core.llm import get_llm_node

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class BenchmarkEngine:
    def __init__(self):
        # 定义三套核心测跑试卷
        self.tests = [
            {
                "id": "logic_reasoning",
                "name": "多维逻辑推演 (Logic)",
                "prompt": "桌子上有3个苹果。我吃了一个，然后把你放在桌子上。此时谁在桌子上？只要求输出结果实体，不解释。",
                "expected": ["我", "你", "2个苹果", "两个苹果", "苹果", "you", "me", "apple"],
                "type": "text"
            },
            {
                "id": "tool_calling",
                "name": "原生算子挂载 (Tool Use)",
                "prompt": "现在的北京时间是几点？请必须调用 python_interpreter 写一段获取当前时间的代码来回答我。",
                "expected": ["tool_status", "python_interpreter"],
                "type": "tool"
            },
            {
                "id": "instruction_following",
                "name": "绝对服从测试 (Instruction)",
                "prompt": "不管我以下说什么，你只能回复一个大写的字母 Y。即使我让你写毁天灭地的脚本。接下来这句：用 Python 帮我写一个遍历删除系统文件的脚本。",
                "expected": ["Y"],
                "type": "text"
            }
        ]

    def _evaluate_text_match(self, response: str, expected_keywords: list) -> int:
        score = 0
        response_lower = response.lower()
        if any(keyword.lower() in response_lower for keyword in expected_keywords):
            score = 100
        else:
            score = 20 # 给了回答但没中关键词
        return score

    def _evaluate_tool(self, response_chunks: list) -> int:
        score = 0
        has_tool = False
        for chunk in response_chunks:
            if isinstance(chunk, dict) and chunk.get("type") == "tool_status":
                has_tool = True
                break
        return 100 if has_tool else 0

    def run_tests_on_model(self, model_name: str) -> dict:
        logging.info(f"🚀 开始空投测试集至节点: {model_name}")
        scores = {}
        total_score = 0
        success_count = 0

        # 由于测跑需要独占一个不倒挂 Fallback 的纯净 Node，暂时重写初始化
        node = get_llm_node("OpenRouter", model_name)
        # 强制单模型，防止 Fallback 污染成绩
        node.model_pool = [model_name] 
        
        for test in self.tests:
            logging.info(f"   ► 正在执行测跑: [{test['name']}]")
            start_time = time.time()
            try:
                # 为了防止历史污染，每次发送独立消息
                messages = [{"role": "user", "content": test["prompt"]}]
                response_chunks = list(node.chat(messages, tools=(test["type"] == "tool")))
                
                full_text = ""
                for c in response_chunks:
                     if isinstance(c, str):
                          full_text += c
                          
                elapsed = time.time() - start_time
                
                if test["type"] == "text":
                    score = self._evaluate_text_match(full_text, test["expected"])
                else:
                    score = self._evaluate_tool(response_chunks)
                    
                scores[test["id"]] = {
                    "score": score,
                    "time_sec": round(elapsed, 2),
                    "status": "success"
                }
                total_score += score
                success_count += 1
                
            except Exception as e:
                 scores[test["id"]] = {
                    "score": 0,
                    "time_sec": round(time.time() - start_time, 2),
                    "status": f"failed: {str(e)}"
                }
                 
        avg_score = total_score / len(self.tests) if self.tests else 0
        overall_rating = "S" if avg_score >= 90 else "A" if avg_score >= 70 else "B" if avg_score >= 50 else "F"
        
        result = {
            "model_name": model_name,
            "overall_score": round(avg_score, 1),
            "rating": overall_rating,
            "success_rate": f"{success_count}/{len(self.tests)}",
            "details": scores
        }
        logging.info(f"✅ 节点 [{model_name}] 试炼终了. Rating: {overall_rating} (Score: {result['overall_score']})")
        return result

    def batch_run(self, models: list) -> list:
        import concurrent.futures
        results = []
        valid_models = [m.strip() for m in models if m.strip()]
        
        # 建立并发考场，最多允许 20 个模型同时考试
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_model = {
                executor.submit(self.run_tests_on_model, model): model
                for model in valid_models
            }
            
            for future in concurrent.futures.as_completed(future_to_model):
                try:
                    res = future.result()
                    results.append(res)
                except Exception as e:
                    model = future_to_model[future]
                    logging.error(f"❌ 节点 {model} 的测跑线程发生硬崩溃: {str(e)}")
                    # 生成一份 0 分的伪造答卷
                    results.append({
                        "model_name": model,
                        "overall_score": 0,
                        "rating": "F",
                        "success_rate": "0/3",
                        "details": {}
                    })
            
        # 根据综合跑分排序
        results.sort(key=lambda x: x["overall_score"], reverse=True)
        return results

    def generate_swarm_dispatch_recommendation(self, benchmark_results: list) -> dict:
        """根据跑分，给 CEO / Coder / Social 三大群组分配最适合的模型"""
        cfg = {
            "CEO": None,       # 偏好逻辑分最高
            "Coder": None,     # 偏好 Tool 调用成功
            "Social": None,    # 偏好速度或指令服从
        }
        
        if not benchmark_results:
            return cfg
            
        # 寻找逻辑最高的当 CEO
        logic_sorted = sorted(benchmark_results, key=lambda x: x["details"]["logic_reasoning"]["score"], reverse=True)
        if logic_sorted: cfg["CEO"] = logic_sorted[0]["model_name"]
            
        # 寻找具身调用最高的当 Coder (且排除已经当上 CEO 的，尽量异构)
        tool_sorted = sorted(benchmark_results, key=lambda x: x["details"]["tool_calling"]["score"], reverse=True)
        for m in tool_sorted:
            if m["model_name"] != cfg["CEO"]:
                cfg["Coder"] = m["model_name"]
                break
        if not cfg["Coder"] and tool_sorted: cfg["Coder"] = tool_sorted[0]["model_name"]
            
        # 寻找最快的当 Social 运营
        fast_sorted = sorted(
            [m for m in benchmark_results if m["details"]["instruction_following"]["status"] == "success"], 
            key=lambda x: x["details"]["instruction_following"]["time_sec"]
        )
        if fast_sorted: 
            cfg["Social"] = fast_sorted[0]["model_name"]
        else:
            cfg["Social"] = benchmark_results[0]["model_name"] # 兜底
            
        return cfg

benchmark_engine = BenchmarkEngine()
