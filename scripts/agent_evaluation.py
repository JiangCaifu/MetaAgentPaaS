# ========================================
# 第11周任务：Agent效果评估脚本
# 定期检测Agent回答质量
# ========================================
import asyncio
import json
import os
import time
from datetime import datetime
from typing import List, Dict, Any

# 添加项目路径
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.graph.dual_rag_qa import dual_enhance_qa
from agent.graph.rag_evaluate import RagasEvaluator
from agent.utils.logging_config import agent_logger, setup_logging

# 测试数据集
TEST_DATASET = [
    {
        "question": "北京有哪些热门景点？",
        "ground_truth": "北京热门景点包括故宫、天安门广场、颐和园、天坛、八达岭长城等。故宫是明清两代的皇家宫殿，是世界上现存规模最大、保存最为完整的木质结构古建筑群。天安门广场是世界上最大的城市广场，是中国重要的政治活动场所。颐和园是中国现存规模最大、保存最完整的皇家园林。",
        "category": "景点查询"
    },
    {
        "question": "世界之窗怎么前往？",
        "ground_truth": "前往世界之窗可以乘坐深圳地铁1号线至世界之窗站下车，也可以乘坐地铁2号线至侨城东站下车后步行前往。此外，还有多路公交车可以到达世界之窗。",
        "category": "交通查询"
    },
    {
        "question": "推荐一些深圳的景点？",
        "ground_truth": "深圳值得推荐的景点有世界之窗、东部华侨城、欢乐谷、锦绣中华、小梅沙海滨浴场等。世界之窗展示了世界各地著名景点的微缩景观，东部华侨城是一个大型生态旅游度假区，欢乐谷是大型主题乐园。",
        "category": "推荐查询"
    },
    {
        "question": "故宫收藏了哪些文物？",
        "ground_truth": "故宫博物院收藏了大量珍贵文物，包括绘画、书法、青铜器、陶瓷、玉器、金银器等。其中著名的文物有《清明上河图》、《千里江山图》、毛公鼎、散氏盘等。故宫的文物收藏总数超过180万件。",
        "category": "文物查询"
    },
    {
        "question": "上海有什么好玩的地方？",
        "ground_truth": "上海好玩的地方有外滩、豫园、东方明珠、上海迪士尼乐园、南京路步行街等。外滩可以欣赏到上海的标志性建筑和黄浦江景色，豫园是江南古典园林的代表，东方明珠是上海的标志性建筑之一。",
        "category": "景点查询"
    },
    {
        "question": "颐和园的开放时间是什么时候？",
        "ground_truth": "颐和园的开放时间通常为08:30-17:00，具体时间可能会根据季节有所调整。建议游客在参观前查看官方网站或拨打咨询电话确认最新的开放时间。",
        "category": "景点查询"
    },
    {
        "question": "从深圳北站怎么去东部华侨城？",
        "ground_truth": "从深圳北站可以乘坐地铁5号线到黄贝岭站，然后转乘地铁2号线到新秀站，出站后步行到公交站乘坐前往东部华侨城的公交车。也可以选择打车或自驾前往。",
        "category": "交通查询"
    },
    {
        "question": "北京有什么历史古迹？",
        "ground_truth": "北京的历史古迹有故宫、天坛、颐和园、八达岭长城、明十三陵、圆明园遗址等。这些古迹见证了中国悠久的历史和灿烂的文化，是北京作为历史文化名城的重要标志。",
        "category": "文物查询"
    }
]

class AgentEvaluator:
    """
    Agent效果评估器
    定期检测Agent回答质量，记录评估结果
    """
    
    def __init__(self):
        self.evaluator = RagasEvaluator()
        self.results = []
        self.summary = {}
    
    async def evaluate_single(self, sample: Dict) -> Dict:
        """
        评估单个测试样本
        :param sample: 测试样本
        :return: 评估结果
        """
        start_time = time.time()
        
        try:
            # 调用Agent获取回答
            response = await dual_enhance_qa(sample["question"])
            answer = response["answer"]
            
            # 收集上下文
            contexts = []
            if response.get("kg_knowledge"):
                contexts.append(response["kg_knowledge"])
            if response.get("vector_reference"):
                contexts.append(response["vector_reference"])
            
            # 使用Ragas评估
            evaluation = self.evaluator.evaluate_single(
                question=sample["question"],
                answer=answer,
                contexts=contexts,
                ground_truth=sample.get("ground_truth", "")
            )
            
            # 记录日志
            agent_logger.log_evaluation("faithfulness", evaluation["faithfulness"], 0.7)
            agent_logger.log_evaluation("relevancy", evaluation["answer_relevancy"], 0.7)
            agent_logger.log_evaluation("precision", evaluation["context_precision"], 0.7)
            agent_logger.log_evaluation("recall", evaluation["context_recall"], 0.7)
            
            duration = time.time() - start_time
            
            return {
                "question": sample["question"],
                "category": sample["category"],
                "answer": answer,
                "ground_truth": sample.get("ground_truth"),
                "evaluation": evaluation,
                "duration": duration,
                "success": True
            }
            
        except Exception as e:
            duration = time.time() - start_time
            agent_logger.log_error("EvaluationError", str(e))
            return {
                "question": sample["question"],
                "category": sample["category"],
                "answer": "",
                "ground_truth": sample.get("ground_truth"),
                "evaluation": {},
                "duration": duration,
                "success": False,
                "error": str(e)
            }
    
    async def run_evaluation(self, dataset: List[Dict] = None) -> Dict:
        """
        运行完整评估
        :param dataset: 测试数据集
        :return: 评估汇总结果
        """
        if dataset is None:
            dataset = TEST_DATASET
        
        agent_logger.logger.info("🚀 开始Agent效果评估")
        agent_logger.logger.info(f"📊 测试样本数: {len(dataset)}")
        
        total_start = time.time()
        self.results = []
        
        for i, sample in enumerate(dataset, 1):
            agent_logger.logger.info(f"🔄 正在评估第 {i}/{len(dataset)} 个样本: {sample['question'][:30]}...")
            result = await self.evaluate_single(sample)
            self.results.append(result)
        
        total_duration = time.time() - total_start
        
        # 计算汇总统计
        self.summary = self._calculate_summary()
        
        # 生成报告
        report = self._generate_report(total_duration)
        
        # 保存报告
        self._save_report(report)
        
        agent_logger.logger.info("✅ Agent效果评估完成")
        
        return {
            "summary": self.summary,
            "results": self.results,
            "report_path": "agent_evaluation_report.txt"
        }
    
    def _calculate_summary(self) -> Dict:
        """
        计算汇总统计
        """
        successful_results = [r for r in self.results if r["success"]]
        
        if not successful_results:
            return {
                "total_samples": len(self.results),
                "success_rate": 0.0,
                "avg_duration": 0.0,
                "avg_faithfulness": 0.0,
                "avg_relevancy": 0.0,
                "avg_precision": 0.0,
                "avg_recall": 0.0,
                "avg_overall": 0.0,
                "grade": "F"
            }
        
        # 计算各项指标平均值
        avg_faithfulness = sum(r["evaluation"]["faithfulness"] for r in successful_results) / len(successful_results)
        avg_relevancy = sum(r["evaluation"]["answer_relevancy"] for r in successful_results) / len(successful_results)
        avg_precision = sum(r["evaluation"]["context_precision"] for r in successful_results) / len(successful_results)
        avg_recall = sum(r["evaluation"]["context_recall"] for r in successful_results) / len(successful_results)
        avg_overall = sum(r["evaluation"]["overall"] for r in successful_results) / len(successful_results)
        avg_duration = sum(r["duration"] for r in successful_results) / len(successful_results)
        
        # 计算成功率
        success_rate = len(successful_results) / len(self.results)
        
        # 确定等级
        grade = self._get_grade(avg_overall)
        
        return {
            "total_samples": len(self.results),
            "success_rate": round(success_rate, 4),
            "avg_duration": round(avg_duration, 2),
            "avg_faithfulness": round(avg_faithfulness, 4),
            "avg_relevancy": round(avg_relevancy, 4),
            "avg_precision": round(avg_precision, 4),
            "avg_recall": round(avg_recall, 4),
            "avg_overall": round(avg_overall, 4),
            "grade": grade
        }
    
    def _get_grade(self, score: float) -> str:
        """
        根据综合分数确定等级
        """
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"
    
    def _generate_report(self, total_duration: float) -> str:
        """
        生成评估报告
        """
        s = self.summary
        
        report = f"""
╔══════════════════════════════════════════════════════════════════════╗
║                   Agent效果评估报告（第11周任务）                    ║
╚══════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────┐
│ 【评估概览】                                                         │
├──────────────────────────────────────────────────────────────────────┤
│  评估时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}              │
│  测试样本数：{s['total_samples']}                                      │
│  成功率：{s['success_rate'] * 100:.2f}%                                │
│  平均耗时：{s['avg_duration']:.2f}秒                                   │
│  总耗时：{total_duration:.2f}秒                                       │
│  综合评级：{s['grade']}                                               │
│  综合分数：{s['avg_overall']:.4f}                                     │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ 【各项指标得分】                                                     │
├──────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┬──────────┬─────────────┐                       │
│  │     指标名称     │   分数   │    状态     │                       │
│  ├─────────────────┼──────────┼─────────────┤                       │
│  │   faithfulness  │ {s['avg_faithfulness']:.4f}   │ {self._get_status(s['avg_faithfulness'])}    │                       │
│  │ answer_relevancy│ {s['avg_relevancy']:.4f}    │ {self._get_status(s['avg_relevancy'])}     │                       │
│  │context_precision│ {s['avg_precision']:.4f}    │ {self._get_status(s['avg_precision'])}     │                       │
│  │ context_recall  │ {s['avg_recall']:.4f}   │ {self._get_status(s['avg_recall'])}    │                       │
│  └─────────────────┴──────────┴─────────────┘                       │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ 【样本详细结果】                                                     │
├──────────────────────────────────────────────────────────────────────┤
"""
        
        for i, result in enumerate(self.results, 1):
            status = "✅" if result["success"] else "❌"
            overall = result["evaluation"].get("overall", 0) if result["success"] else 0
            
            report += f"""│ {status} 样本{i}: {result['question'][:40]}...
│     分类：{result['category']}
│     耗时：{result['duration']:.2f}秒
"""
            if result["success"]:
                report += f"""│     综合评分：{overall:.4f}
│     忠实度：{result['evaluation']['faithfulness']:.4f}
│     相关性：{result['evaluation']['answer_relevancy']:.4f}
"""
            else:
                report += f"""│     错误：{result['error'][:50]}...
"""
            report += "│\n"
        
        report += """└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ 【优化建议】                                                         │
├──────────────────────────────────────────────────────────────────────┤
"""
        
        suggestions = self._generate_suggestions()
        for suggestion in suggestions:
            report += f"│ {suggestion}\n"
        
        report += """└──────────────────────────────────────────────────────────────────────┘

╔══════════════════════════════════════════════════════════════════════╗
║                         评估完成                                     ║
╚══════════════════════════════════════════════════════════════════════╝
"""
        
        return report
    
    def _get_status(self, score: float) -> str:
        """
        获取指标状态图标
        """
        if score >= 0.8:
            return "✅ 优秀"
        elif score >= 0.6:
            return "⚠️ 一般"
        else:
            return "❌ 较差"
    
    def _generate_suggestions(self) -> List[str]:
        """
        生成优化建议
        """
        suggestions = []
        s = self.summary
        
        if s["avg_faithfulness"] < 0.7:
            suggestions.append("• 增强上下文约束，减少幻觉：优化prompt模板，增加事实核查步骤")
        
        if s["avg_relevancy"] < 0.7:
            suggestions.append("• 提高回答相关性：优化检索策略，调整top_k参数")
        
        if s["avg_precision"] < 0.7:
            suggestions.append("• 提高上下文利用率：优化重排算法，提升检索精准度")
        
        if s["avg_recall"] < 0.7:
            suggestions.append("• 提高信息召回率：扩充知识图谱和向量知识库")
        
        if s["success_rate"] < 0.8:
            suggestions.append("• 提高系统稳定性：检查API调用频率限制，增加重试机制")
        
        if s["avg_duration"] > 5.0:
            suggestions.append("• 优化响应速度：考虑缓存热门查询结果")
        
        if not suggestions:
            suggestions.append("• 当前各项指标良好，建议继续保持")
        
        suggestions.extend([
            "• 扩充知识图谱实体与关系，提升结构化召回率",
            "• 增大向量知识库文旅文档体量",
            "• 定期运行评估脚本，监控Agent效果变化"
        ])
        
        return suggestions
    
    def _save_report(self, report: str):
        """
        保存评估报告到文件
        """
        report_dir = "reports"
        if not os.path.exists(report_dir):
            os.makedirs(report_dir)
        
        report_path = os.path.join(report_dir, f"agent_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        
        agent_logger.logger.info(f"📄 评估报告已保存：{report_path}")

async def main():
    """
    主函数：运行Agent效果评估
    """
    # 初始化日志
    setup_logging("INFO")
    
    # 创建评估器并运行
    evaluator = AgentEvaluator()
    result = await evaluator.run_evaluation()
    
    # 打印汇总结果
    print("\n" + "="*60)
    print("Agent效果评估汇总")
    print("="*60)
    print(f"测试样本数: {result['summary']['total_samples']}")
    print(f"成功率: {result['summary']['success_rate'] * 100:.2f}%")
    print(f"综合评级: {result['summary']['grade']}")
    print(f"综合分数: {result['summary']['avg_overall']:.4f}")
    print(f"报告文件: {result['report_path']}")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
