#!/usr/bin/env python3
"""
Скрипт для извлечения текста из PDF книги "Восхождение"
"""

import pdfplumber
import json
import re
from pathlib import Path

def extract_pdf_content(pdf_path: str) -> dict:
    """Извлечение содержимого из PDF файла"""
    
    content = {
        'title': 'Восхождение',
        'author': 'HR-Психоаналитик',
        'chapters': [],
        'full_text': '',
        'key_concepts': [],
        'analysis_methods': []
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Обрабатываем PDF: {len(pdf.pages)} страниц")
            
            full_text = ""
            current_chapter = None
            current_content = []
            
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if not text:
                    continue
                
                full_text += text + "\n"
                
                # Ищем заголовки глав
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    
                    # Определяем заголовки глав (обычно заглавными буквами или с номерами)
                    if (line.isupper() and len(line) > 10) or \
                       re.match(r'^[Гг]лава\s+\d+', line) or \
                       re.match(r'^\d+\.\s+[А-Я]', line):
                        
                        # Сохраняем предыдущую главу
                        if current_chapter and current_content:
                            content['chapters'].append({
                                'title': current_chapter,
                                'content': '\n'.join(current_content),
                                'page': page_num + 1
                            })
                        
                        # Начинаем новую главу
                        current_chapter = line
                        current_content = []
                    
                    elif current_chapter:
                        current_content.append(line)
            
            # Сохраняем последнюю главу
            if current_chapter and current_content:
                content['chapters'].append({
                    'title': current_chapter,
                    'content': '\n'.join(current_content),
                    'page': page_num + 1
                })
            
            content['full_text'] = full_text
            
            # Извлекаем ключевые концепции
            content['key_concepts'] = extract_key_concepts(full_text)
            
            # Извлекаем методы анализа
            content['analysis_methods'] = extract_analysis_methods(full_text)
            
            print(f"Извлечено {len(content['chapters'])} глав")
            print(f"Общий объем текста: {len(full_text)} символов")
            
    except Exception as e:
        print(f"Ошибка при обработке PDF: {e}")
        return None
    
    return content

def extract_key_concepts(text: str) -> list:
    """Извлечение ключевых концепций из текста"""
    
    concepts = []
    
    # Паттерны для поиска ключевых концепций
    patterns = [
        r'самооценк[аи]',
        r'психотип[аы]?',
        r'архетип[аы]?',
        r'защитн[ыые]\s+механизм[ыы]?',
        r'бессознательн[оаые]',
        r'личност[ьи]',
        r'характер[аы]?',
        r'темперамент[аы]?',
        r'эмоциональн[оаые]',
        r'когнитивн[оаые]',
        r'поведенческ[оаые]',
        r'адаптивн[оаые]',
        r'трансформаци[ия]',
        r'развити[ея]',
        r'потенциал[аы]?',
        r'ресурс[ыы]?',
        r'ограничени[яя]',
        r'блокировк[ии]',
        r'страх[иы]?',
        r'тревог[аы]?',
        r'стресс[аы]?',
        r'депресси[ия]',
        r'мотиваци[ия]',
        r'цели\s+и\s+задачи',
        r'ценност[иы]?',
        r'убеждени[яя]',
        r'установк[ии]'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text.lower())
        if matches:
            concepts.extend(matches)
    
    return list(set(concepts))

def extract_analysis_methods(text: str) -> list:
    """Извлечение методов анализа из текста"""
    
    methods = []
    
    # Паттерны для поиска методов анализа
    patterns = [
        r'психоанализ[аы]?',
        r'аналитическая\s+психология',
        r'когнитивно-поведенческая\s+терапия',
        r'гештальт-терапи[ия]',
        r'транзакционный\s+анализ',
        r'системная\s+терапи[ия]',
        r'семейная\s+терапи[ия]',
        r'групповая\s+терапи[ия]',
        r'арт-терапи[ия]',
        r'музыкотерапи[ия]',
        r'танцевальная\s+терапи[ия]',
        r'медитаци[ия]',
        r'релаксаци[ия]',
        r'дыхательные\s+упражнения',
        r'визуализаци[ия]',
        r'аффирмаци[ия]',
        r'позитивное\s+мышление',
        r'когнитивная\s+реструктуризация',
        r'работа\s+с\s+эмоциями',
        r'эмоциональная\s+регуляция',
        r'стресс-менеджмент',
        r'тайм-менеджмент',
        r'целеполагание',
        r'планирование',
        r'самоанализ',
        r'рефлексия',
        r'дневник\s+эмоций',
        r'дневник\s+мыслей',
        r'дневник\s+поведения'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text.lower())
        if matches:
            methods.extend(matches)
    
    return list(set(methods))

def save_extracted_content(content: dict, output_path: str):
    """Сохранение извлеченного содержимого в JSON файл"""
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        print(f"Содержимое сохранено в {output_path}")
    except Exception as e:
        print(f"Ошибка при сохранении: {e}")

if __name__ == "__main__":
    # Путь к PDF файлу
    pdf_path = "Книга Восхождение.pdf"
    
    if not Path(pdf_path).exists():
        print(f"PDF файл не найден: {pdf_path}")
        exit(1)
    
    # Извлекаем содержимое
    content = extract_pdf_content(pdf_path)
    
    if content:
        # Сохраняем в JSON файл
        output_path = "data/book_content.json"
        Path("data").mkdir(exist_ok=True)
        save_extracted_content(content, output_path)
        
        # Выводим статистику
        print(f"\n=== СТАТИСТИКА ===")
        print(f"Глав: {len(content['chapters'])}")
        print(f"Ключевых концепций: {len(content['key_concepts'])}")
        print(f"Методов анализа: {len(content['analysis_methods'])}")
        print(f"Общий объем текста: {len(content['full_text'])} символов")
        
        # Показываем первые несколько концепций и методов
        print(f"\n=== КЛЮЧЕВЫЕ КОНЦЕПЦИИ ===")
        for concept in content['key_concepts'][:10]:
            print(f"- {concept}")
        
        print(f"\n=== МЕТОДЫ АНАЛИЗА ===")
        for method in content['analysis_methods'][:10]:
            print(f"- {method}")
    else:
        print("Не удалось извлечь содержимое из PDF")
