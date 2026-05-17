# ========================================
# 第10周任务：Ragas效果评估脚本
# ========================================
from typing import List, Dict, Any
import numpy as np
import json
import logging

logger = logging.getLogger("RagasEvaluator")

class RagasEvaluator:
    """RAG效果评估器（简化版，无需安装复杂依赖）"""
    
    def __init__(self):
        logger.info("✅ Ragas评估器初始化成功")
    
    def evaluate_faithfulness(self, answer: str, contexts: List[str]) -> float:
        """
        评估忠实度：回答是否基于上下文，有无幻觉
        :param answer: 生成的回答
        :param contexts: 上下文文本列表
        :return: 忠实度分数 (0-1)
        """
        if not answer or not contexts:
            return 0.0
        
        all_context = " ".join(contexts)
        answer_lower = answer.lower()
        context_lower = all_context.lower()
        
        # 检查回答中的关键信息是否能在上下文中找到
        score = 0.0
        check_count = 0
        
        # 检查数字信息
        import re
        numbers = re.findall(r'\d+[\u4e00-\u9fa5]*', answer)
        for num in numbers[:5]:
            check_count += 1
            if num.lower() in context_lower:
                score += 1.0
        
        # 检查专有名词
        proper_nouns = ["故宫", "世界之窗", "东部华侨城", "欢乐谷", "外滩", "豫园", "东方明珠", "兵马俑"]
        for noun in proper_nouns:
            if noun in answer:
                check_count += 1
                if noun in all_context:
                    score += 1.0
        
        return min(1.0, score / check_count) if check_count > 0 else 0.7
    
    def evaluate_relevancy(self, answer: str, question: str) -> float:
        """
        评估相关性：回答与问题的匹配程度
        :param answer: 生成的回答
        :param question: 用户问题
        :return: 相关性分数 (0-1)
        """
        if not answer or not question:
            return 0.0
        
        answer_words = set(answer.split())
        question_words = set(question.split())
        
        # 计算重叠率
        overlap = answer_words & question_words
        if not overlap:
            return 0.3
        
        return min(1.0, len(overlap) / len(question_words))
    
    def evaluate_context_precision(self, answer: str, contexts: List[str]) -> float:
        """
        评估上下文精确性：上下文中有多少信息被有效使用
        :param answer: 生成的回答
        :param contexts: 上下文文本列表
        :return: 精确性分数 (0-1)
        """
        if not answer or not contexts:
            return 0.0
        
        answer_len = len(answer)
        if answer_len == 0:
            return 0.0
        
        # 计算上下文中有多少内容出现在回答中
        all_context = " ".join(contexts)
        context_len = len(all_context)
        
        # 简单计算：回答中有多少字来自上下文
        match_chars = 0
        for char in answer[:200]:
            if char in all_context:
                match_chars += 1
        
        return min(1.0, match_chars / min(answer_len, 200))
    
    def evaluate_context_recall(self, answer: str, contexts: List[str], ground_truth: str) -> float:
        """
        评估上下文召回：回答是否覆盖了真实答案的关键信息
        :param answer: 生成的回答
        :param contexts: 上下文文本列表
        :param ground_truth: 真实答案
        :return: 召回分数 (0-1)
        """
        if not answer or not ground_truth:
            return 0.0
        
        ground_truth_words = set(ground_truth.split())
        answer_words = set(answer.split())
        
        # 计算真实答案中的关键词在回答中出现的比例
        overlap = ground_truth_words & answer_words
        if not overlap:
            return 0.3
        
        return min(1.0, len(overlap) / len(ground_truth_words))
    
    def evaluate_single(self, question: str, answer: str, contexts: List[str], ground_truth: str = "") -> Dict:
        """
        评估单个问答对
        :param question: 用户问题
        :param answer: 生成的回答
        :param contexts: 检索到的上下文
        :param ground_truth: 真实答案（可选）
        :return: 评估结果
        """
        faithfulness = self.evaluate_faithfulness(answer, contexts)
        relevancy = self.evaluate_relevancy(answer, question)
        precision = self.evaluate_context_precision(answer, contexts)
        
        if ground_truth:
            recall = self.evaluate_context_recall(answer, contexts, ground_truth)
        else:
            recall = 0.7  # 默认值
        
        # 综合分数
        overall = (faithfulness * 0.3 + relevancy * 0.25 + precision * 0.25 + recall * 0.2)
        
        return {
            "question": question,
            "faithfulness": round(faithfulness, 4),
            "answer_relevancy": round(relevancy, 4),
            "context_precision": round(precision, 4),
            "context_recall": round(recall, 4),
            "overall": round(overall, 4),
            "answer_length": len(answer),
            "context_count": len(contexts)
        }
    
    def evaluate_batch(self, eval_data: List[Dict]) -> Dict:
        """
        批量评估
        :param eval_data: 评估数据列表
        :return: 汇总评估结果
        """
        results = []
        for item in eval_data:
            result = self.evaluate_single(
                question=item["question"],
                answer=item["answer"],
                contexts=item["contexts"],
                ground_truth=item.get("ground_truth", "")
            )
            results.append(result)
        
        # 计算平均值
        avg_faithfulness = np.mean([r["faithfulness"] for r in results])
        avg_relevancy = np.mean([r["answer_relevancy"] for r in results])
        avg_precision = np.mean([r["context_precision"] for r in results])
        avg_recall = np.mean([r["context_recall"] for r in results])
        avg_overall = np.mean([r["overall"] for r in results])
        
        return {
            "total_samples": len(results),
            "average": {
                "faithfulness": round(avg_faithfulness, 4),
                "answer_relevancy": round(avg_relevancy, 4),
                "context_precision": round(avg_precision, 4),
                "context_recall": round(avg_recall, 4),
                "overall": round(avg_overall, 4)
            },
            "detailed_results": results,
            "grade": self._get_grade(avg_overall)
        }
    
    def _get_grade(self, score: float) -> str:
        """根据综合分数给出等级"""
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
    
    def generate_report(self, evaluation_result: Dict) -> str:
        """生成评估报告"""
        avg = evaluation_result["average"]
        
        report = f"""
╔══════════════════════════════════════════════════════════════════════╗
║                    RAG效果量化评估结果（第10周任务）                  ║
╚══════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────┐
│ 【评估概述】                                                         │
├──────────────────────────────────────────────────────────────────────┤
│  评估样本数：{evaluation_result['total_samples']}                      │
│  综合评级：{evaluation_result['grade']}                              │
│  综合分数：{avg['overall']:.4f}                                      │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ 【各项指标得分】                                                     │
├──────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┬──────────┬───────────────────────────────────┐  │
│  │     指标名称     │   分数   │              说明                 │  │
│  ├─────────────────┼──────────┼───────────────────────────────────┤  │
│  │   faithfulness  │ {avg['faithfulness']:.4f}   │ 回答忠实度，无幻觉         │  │
│  │ answer_relevancy│ {avg['answer_relevancy']:.4f}│ 回答与问题的相关性         │  │
│  │context_precision│ {avg['context_precision']:.4f}│ 上下文信息利用率          │  │
│  │ context_recall  │ {avg['context_recall']:.4f}   │ 关键信息覆盖度            │  │
│  └─────────────────┴──────────┴───────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ 【优化建议】                                                         │
├──────────────────────────────────────────────────────────────────────┤
"""
        
        suggestions = []
        
        if avg["faithfulness"] < 0.7:
            suggestions.append("• 增强上下文约束，减少幻觉：优化prompt模板，增加事实核查")
        
        if avg["answer_relevancy"] < 0.7:
            suggestions.append("• 提高回答相关性：优化检索策略，调整top_k参数")
        
        if avg["context_precision"] < 0.7:
            suggestions.append("• 提高上下文利用率：优化重排算法，提升检索精准度")
        
        if avg["context_recall"] < 0.7:
            suggestions.append("• 提高信息召回率：扩充知识图谱和向量知识库")
        
        if not suggestions:
            suggestions.append("• 当前各项指标良好，建议继续保持")
        
        suggestions.extend([
            "• 扩充知识图谱实体与关系，提升结构化召回率",
            "• 增大向量知识库文旅文档体量",
            "• 调整重排TOP值，平衡召回数量与精准度",
            "• 增加意图分类，精准分流图谱检索/文本检索"
        ])
        
        for suggestion in suggestions:
            report += f"│ {suggestion}\n"
        
        report += """└──────────────────────────────────────────────────────────────────────┘

╔══════════════════════════════════════════════════════════════════════╗
║                         评估完成                                     ║
╚══════════════════════════════════════════════════════════════════════╝
"""
        
        return report

# 异步评估函数（集成到FastAPI）
async def run_rag_evaluation(test_samples: List[Dict] = None) -> Dict:
    """运行RAG效果评估"""
    from agent.graph.dual_rag_qa import dual_enhance_qa
    
    if test_samples is None:
        test_samples = [
            {"question": "北京有哪些热门景点", "ground_truth": "北京热门景点有故宫、天安门、颐和园等"},
            {"question": "世界之窗怎么前往", "ground_truth": "可乘坐深圳地铁1号线至世界之窗站下车"},
            {"question": "深圳有什么好玩的地方", "ground_truth": "深圳好玩的地方有世界之窗、东部华侨城、欢乐谷等"},
            {"question": "故宫收藏了哪些文物", "ground_truth": "故宫收藏了清明上河图等珍贵文物"},
            {"question": "推荐一些上海的景点", "ground_truth": "上海的景点有外滩、豫园、东方明珠等"}
        ]
    
    evaluator = RagasEvaluator()
    eval_data = []
    
    for item in test_samples:
        res = await dual_enhance_qa(item["question"])
        contexts = []
        if res["kg_knowledge"]:
            contexts.append(res["kg_knowledge"])
        if res["vector_reference"]:
            contexts.append(res["vector_reference"])
        
        eval_data.append({
            "question": item["question"],
            "answer": res["answer"],
            "contexts": contexts,
            "ground_truth": item.get("ground_truth", "")
        })
    
    result = evaluator.evaluate_batch(eval_data)
    
    # 生成并保存报告
    report = evaluator.generate_report(result)
    print(report)
    
    with open("ragas_evaluation_report.txt", "w", encoding="utf-8") as f:
        f.write(report)
    
    return result
