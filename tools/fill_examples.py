"""
例句填充脚本 - 为缺少例句的单词生成例句
根据词性生成不同类型的诗意化例句模板
"""

import logging
import random
import re
from typing import Dict, List, Optional

from .words_crud import WordsCRUD

logger = logging.getLogger(__name__)

# 诗意化例句模板库（按词性分类）
# 设计原则：意象丰富、情感共鸣、文学感强、哲理内涵
EXAMPLE_TEMPLATES = {
    # 名词模板 - 场景化、意境化，创造画面感
    "n": [
        "In the quiet hours of dawn, a single {word} holds the promise of a new beginning.",
        "The {word}, touched by golden light, became a moment worth remembering.",
        "She found beauty in the simplest {word}, as if the universe whispered its secrets.",
        "Time has a way of transforming a mere {word} into something extraordinary.",
        "The {word} stood there, silent witness to countless stories untold.",
        "Sometimes the most precious {word} is the one we almost overlooked.",
        "In her eyes, that {word} held memories of a thousand yesterdays.",
        "The {word} appeared ordinary, yet carried the weight of unspoken dreams.",
        "Life often hides its greatest treasures in the simplest {word}.",
        "The {word} remained, a gentle reminder that some things endure.",
        "Like a {word} in the vast universe, we are small yet significant.",
        "She treasured the {word} as if it were the last of its kind.",
        "The old {word} carried stories that only silence could tell.",
        "Every {word} has a story waiting to be discovered.",
        "The {word} gleamed softly, a beacon in the gathering dusk.",
    ],

    # 动词模板 - 动作意境化，赋予哲学意味
    "v": [
        "To {word} is to embrace the unknown with courage and grace.",
        "She chose to {word}, knowing that every journey begins with a single step.",
        "They say those who {word} with passion leave footprints in time.",
        "In moments of doubt, she would {word} and find her way back to hope.",
        "Learning to {word} taught him that growth comes from courage.",
        "We {word} not because it's easy, but because it matters.",
        "Sometimes we must {word} to discover who we truly are.",
        "The bravest thing we can do is {word} into uncertainty.",
        "She learned to {word} before she could speak of strength.",
        "Every day, he would {word} as if the universe were listening.",
        "To {word} requires more than skill—it requires heart.",
        "When you {word} with intention, the world shifts around you.",
        "They gathered to {word}, united by a shared dream.",
        "She would {word} each morning, a ritual of renewal.",
        "The courage to {word} transformed his entire perspective.",
    ],

    # 形容词模板 - 描写意境化，营造氛围
    "adj": [
        "The {word} morning light painted everything in shades of possibility.",
        "She wore her {word} moments like a crown of experiences.",
        "There's something deeply {word} about the way autumn leaves dance.",
        "The world seemed more {word} through the lens of gratitude.",
        "In that {word} instant, everything became clear.",
        "The {word} sunset reminded her that endings can be beautiful too.",
        "He spoke in {word} tones that echoed long after he left.",
        "The most {word} journeys are often the ones we never planned.",
        "She found the {word} beauty in what others overlooked.",
        "Time has a {word} way of revealing what truly matters.",
        "The {word} sky held secrets of distant worlds.",
        "There was something {word} in the way she smiled.",
        "A {word} heart sees beauty where others see nothing.",
        "The garden was {word}, alive with whispered promises.",
        "She moved through the {word} landscape like a dream.",
    ],

    # 副词模板 - 动作修饰，增添韵律
    "adv": [
        "She walked {word}, as if each step were a meditation.",
        "The leaves fell {word}, dancing their last dance with grace.",
        "He spoke {word}, each word carrying the weight of experience.",
        "Time moved {word} that evening, as if reluctant to let the moment pass.",
        "They lived {word}, embracing each day as a gift.",
        "The river flowed {word}, carrying stories from distant mountains.",
        "She smiled {word}, her eyes holding secrets of a thousand sunsets.",
        "The seasons changed {word}, teaching us that nothing stays the same.",
        "He worked {word}, knowing that mastery comes with patience.",
        "The sun set {word}, painting the sky in hues of farewell.",
        "The wind whispered {word} through the ancient trees.",
        "She breathed {word}, savoring the sweetness of the moment.",
        "The stars twinkled {word} in the velvet night.",
        "He listened {word}, as if each word were a precious gift.",
        "The waves crashed {word} against the patient shore.",
    ],

    # 介词模板 - 空间关系，营造意象
    "prep": [
        "She found peace {word} the noise of the city.",
        "The answer lies {word} the silence of our hearts.",
        "Sometimes we must stand {word} the world to truly see it.",
        "Hope exists {word} despair, waiting to be discovered.",
        "The path winds {word} ancient trees that whisper forgotten tales.",
        "Light finds its way {word} the darkest cracks.",
        "She walked {word} the shadows, unafraid of what lay ahead.",
        "The truth often hides {word} what we refuse to see.",
        "Dreams float {word} reality and imagination.",
        "The stars shine {word} us, ancient guides in the night.",
        "She stood {word} the threshold, ready to begin.",
        "The secret rested {word} the pages of an old book.",
        "Beauty exists {word} the ordinary, waiting to be seen.",
        "He found himself {word} the crossroads of choice.",
        "The memory lingered {word} the edges of her mind.",
    ],

    # 代词模板（无需占位符，完整句式）
    "pron": [
        "He who seeks, finds; she who waits, discovers.",
        "They came not to conquer, but to understand.",
        "We are the authors of our own stories.",
        "It is in giving that we receive the most.",
        "She believed in herself when no one else did.",
        "They who wander are not always lost.",
        "We carry within us the power to change.",
        "He who plants a tree, plants hope.",
        "She who dances to her own rhythm finds true joy.",
        "They say that we become what we believe.",
        "Each of us holds a universe within.",
        "Someone once said that we see the world not as it is, but as we are.",
        "Nobody can go back and start a new beginning.",
        "Everyone you meet knows something you don't.",
        "Nothing is more powerful than an idea whose time has come.",
    ],

    # 连词模板 - 关系表达，哲理思辨
    "conj": [
        "She smiled, {word} in her eyes lived a thousand unspoken words.",
        "Time heals, {word} only if we let it.",
        "He dreamed big, {word} he worked even harder.",
        "Life is beautiful, {word} it is also unpredictable.",
        "She loved the rain, {word} in it she found peace.",
        "We grow, {word} we also lose parts of ourselves.",
        "The stars shine, {word} the darkness makes them visible.",
        "He was afraid, {word} he took the leap anyway.",
        "She hoped for the best, {word} prepared for anything.",
        "They knew the risks, {word} they chose courage.",
        "The mountain was high, {word} her determination was higher.",
        "It was late, {word} the conversation was worth every moment.",
        "The road was long, {word} each step revealed new wonders.",
        "She was tired, {word} she refused to give up.",
        "The task was difficult, {word} together they succeeded.",
    ],

    # 冠词模板（完整句式，无需占位符）
    "art": [
        "A single moment can change everything.",
        "The universe conspires to help those who dare.",
        "An open heart attracts the most beautiful surprises.",
        "The journey of a thousand miles begins with a single step.",
        "A true friend sees the beauty in our scars.",
        "The night sky holds infinite possibilities.",
        "An act of kindness ripples through eternity.",
        "The most beautiful things in life cannot be seen.",
        "A dream written down becomes a goal.",
        "The sun always rises for those who wait.",
        "A word of encouragement can save a life.",
        "The smallest deed is better than the greatest intention.",
        "An obstacle is often a stepping stone in disguise.",
        "The only limit is the one we set ourselves.",
        "A candle loses nothing by lighting another candle.",
    ],

    # 默认模板（用于未知词性）
    "default": [
        "{word}—a word that carries worlds within its letters.",
        "In the story of life, {word} appears as a turning point.",
        "She discovered that {word} meant more than dictionaries could define.",
        "The word '{word}' echoed in her mind like an ancient melody.",
        "Sometimes {word} is the key that unlocks understanding.",
        "He wrote {word} in the margins of his favorite book.",
        "{word} became the bridge between two worlds.",
        "She whispered {word} as if it were a sacred incantation.",
        "The concept of {word} transformed everything she knew.",
        "{word}—simple in form, infinite in meaning.",
        "There's a certain magic in the word {word} that words cannot capture.",
        "She carried {word} with her like a secret garden.",
        "The meaning of {word} deepened with each passing year.",
        "{word}—a single word, yet it held an entire universe.",
        "He found {word} in the spaces between heartbeats.",
    ],
}


def get_pos_category(pos: Optional[str]) -> str:
    """
    根据词性字段返回模板类别

    Args:
        pos: 词性字段（如 'n', 'v', 'adj' 等）

    Returns:
        模板类别
    """
    if not pos:
        return "default"

    # 清理词性字段（去掉前缀如 'n.', 'vt.' 等）
    pos_clean = pos.strip().lower()
    if "." in pos_clean:
        pos_clean = pos_clean.split(".")[0]

    # 映射词性
    pos_mapping = {
        "n": "n",
        "v": "v",
        "vt": "v",
        "vi": "v",
        "adj": "adj",
        "a": "adj",
        "adv": "adv",
        "prep": "prep",
        "pron": "pron",
        "p": "pron",
        "conj": "conj",
        "art": "art",
    }

    return pos_mapping.get(pos_clean, "default")


def generate_example(word: str, pos: Optional[str] = None, translation: Optional[str] = None) -> str:
    """
    为单词生成诗意化例句

    Args:
        word: 单词
        pos: 词性
        translation: 中文翻译（暂未使用，可扩展）

    Returns:
        生成的例句
    """
    category = get_pos_category(pos)
    templates = EXAMPLE_TEMPLATES.get(category, EXAMPLE_TEMPLATES["default"])

    # 使用随机选择模板，增加多样性
    # 结合单词首字母和随机因子，保证可复现性同时增加变化
    random.seed(hash(word) % (2**31))  # 同一单词使用相同种子，保证可复现
    template = random.choice(templates)

    # 处理冠词和代词的特殊情况（无需替换占位符）
    if category in ["art", "pron"]:
        return template

    # 对于动词，需要考虑时态变化（简化处理）
    if category == "v":
        # 大多数动词模板已经处理了形式
        return template.replace("{word}", word)

    # 其他词性直接替换占位符
    return template.replace("{word}", word)


def fill_all_examples(limit: int = None, batch_size: int = 100) -> Dict[str, int]:
    """
    为所有缺少例句的单词填充例句

    Args:
        limit: 处理数量限制（用于测试）
        batch_size: 批处理大小

    Returns:
        统计信息
    """
    crud = WordsCRUD()

    # 获取所有单词
    total_words = crud.list_all(limit=limit or 5000)

    # 筛选缺少例句的单词
    words_without_examples = [
        w for w in total_words
        if not w.get("example_sentence") or not w["example_sentence"].strip()
    ]

    if not words_without_examples:
        logger.info("所有单词已有例句")
        return {"total": len(total_words), "filled": 0, "skipped": len(total_words)}

    logger.info(f"发现 {len(words_without_examples)} 个单词缺少例句")

    # 批量填充
    filled_count = 0
    for i, word in enumerate(words_without_examples):
        try:
            example = generate_example(
                word["word"],
                word.get("pos"),
                word.get("translation")
            )

            # 更新数据库
            crud.update(word["id"], example_sentence=example)
            filled_count += 1

            if (i + 1) % batch_size == 0:
                logger.info(f"已处理 {i + 1}/{len(words_without_examples)} 个单词")

        except Exception as e:
            logger.error(f"处理单词 {word['word']} 时出错: {e}")

    logger.info(f"例句填充完成，共填充 {filled_count} 个单词")

    return {
        "total": len(total_words),
        "without_examples": len(words_without_examples),
        "filled": filled_count,
        "failed": len(words_without_examples) - filled_count,
    }


def main():
    """
    主函数 - 运行例句填充
    """
    print("=" * 50)
    print("SmartVocab 例句填充脚本")
    print("=" * 50)

    stats = fill_all_examples()

    print("\n填充统计:")
    print(f"  总单词数: {stats['total']}")
    print(f"  缺少例句: {stats['without_examples']}")
    print(f"  已填充: {stats['filled']}")
    print(f"  失败: {stats['failed']}")

    # 验证填充结果
    print("\n验证结果...")
    crud = WordsCRUD()
    words = crud.list_all(limit=10)
    for w in words:
        example = w.get("example_sentence", "N/A")
        print(f"  {w['word']}: {example[:50] if example else 'N/A'}")


if __name__ == "__main__":
    main()