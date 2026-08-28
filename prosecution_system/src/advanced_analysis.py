# -*- coding: utf-8 -*-
"""高级分析模块"""
import math
from typing import Dict, List, Tuple
from collections import Counter, defaultdict
from datetime import datetime

class SimilarityAnalyzer:
    WEIGHTS = {'crime': 2.0, 'sentence_range': 1.5, 'circumstances': 1.0, 'region': 0.5}
    
    @classmethod
    def calculate_similarity(cls, c1: Dict, c2: Dict) -> float:
        score = 0.0
        total = sum(cls.WEIGHTS.values())
        if c1.get('crime') == c2.get('crime'): score += cls.WEIGHTS['crime']
        y1, y2 = c1.get('sentence_years', 0), c2.get('sentence_years', 0)
        if y1 and y2:
            d = abs(y1 - y2)
            score += cls.WEIGHTS['sentence_range'] * (1.0 if d == 0 else 0.7 if d <= 1 else 0.3 if d <= 3 else 0)
        factors = ['is_初犯', 'is_累犯', 'is_自首', 'is_坦白', 'is_认罪', 'is_赔偿']
        matches = sum(1 for f in factors if c1.get(f) == c2.get(f) and c1.get(f))
        if matches: score += cls.WEIGHTS['circumstances'] * (matches / len(factors))
        if c1.get('province') == c2.get('province'): score += cls.WEIGHTS['region']
        return min(score / total, 1.0)
    
    @classmethod
    def find_similar(cls, target: Dict, pool: List[Dict], n: int = 5) -> List[Tuple[Dict, float]]:
        sims = [(c, cls.calculate_similarity(target, c)) for c in pool if c.get('case_id') != target.get('case_id')]
        sims.sort(key=lambda x: x[1], reverse=True)
        return sims[:n]

class TrendAnalyzer:
    @classmethod
    def analyze(cls, cases: List[Dict], crime: str = None) -> Dict:
        filtered = [c for c in cases if not crime or c.get('crime') == crime]
        by_month = defaultdict(list)
        for case in filtered:
            d = case.get('case_date', '')
            if d:
                try: by_month[datetime.strptime(d[:7], '%Y-%m').strftime('%Y-%m')].append(case)
                except: pass
        trend = []
        for m in sorted(by_month.keys()):
            mc = by_month[m]
            yrs = [c.get('sentence_years', 0) for c in mc if c.get('sentence_years')]
            trend.append({'month': m, 'count': len(mc), 'avg': sum(yrs)/len(yrs) if yrs else 0})
        return {'crime': crime, 'trend': trend, 'total': len(filtered)}
    
    @classmethod
    def predict(cls, cases: List[Dict], new_case: Dict) -> Dict:
        sims = SimilarityAnalyzer.find_similar(new_case, cases, 10)
        if not sims: return {"error": "无足够相似案例"}
        total_w, weighted = 0, 0
        for case, sim in sims:
            w = sim ** 2
            if case.get('sentence_years'):
                weighted += case['sentence_years'] * w
                total_w += w
        return {'predicted': round(weighted / total_w if total_w else 0, 2), 'confidence': round(sims[0][1], 2)}

class AnomalyDetector:
    @classmethod
    def detect(cls, cases: List[Dict], crime: str = None, threshold: float = 2.0) -> List[Dict]:
        filtered = [c for c in cases if not crime or c.get('crime') == crime]
        years = [c.get('sentence_years', 0) for c in filtered if c.get('sentence_years')]
        if len(years) < 3: return []
        mean = sum(years) / len(years)
        std = math.sqrt(sum((y - mean)**2 for y in years) / len(years))
        anomalies = []
        for case in filtered:
            cy = case.get('sentence_years', 0)
            if cy:
                z = abs((cy - mean) / std) if std else 0
                if z > threshold:
                    anomalies.append({'case': case, 'z_score': round(z, 2), 'deviation': round(cy - mean, 2)})
        return sorted(anomalies, key=lambda x: x['z_score'], reverse=True)

class StatisticsEngine:
    @classmethod
    def analyze(cls, cases: List[Dict]) -> Dict:
        if not cases: return {"error": "无案例数据"}
        years = [c.get('sentence_years', 0) for c in cases if c.get('sentence_years')]
        return {
            'total': len(cases), 'crimes': len(Counter(c.get('crime') for c in cases)),
            'sentencing': {'avg': round(sum(years)/len(years), 2) if years else 0, 'max': max(years) if years else 0, 'min': min(years) if years else 0},
            'crime_dist': dict(Counter(c.get('crime') for c in cases).most_common(10)),
            'province_dist': dict(Counter(c.get('province') for c in cases if c.get('province')).most_common(10)),
        }
