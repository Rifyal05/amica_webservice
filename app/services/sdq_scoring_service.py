import numpy as np
from typing import List

class SdqScoringService:
    _instance = None
    
    # Peta skor SDQ: (indeks pertanyaan, skala, apakah di-reverse)
    SCORING_MAP = [
        (0, 'prosocial', False), (1, 'hyperactivity', False), (2, 'emotional', False), 
        (3, 'prosocial', False), (4, 'conduct', False), (5, 'peer', False), 
        (6, 'conduct', True), (7, 'emotional', False), (8, 'prosocial', False), 
        (9, 'hyperactivity', False), (10, 'peer', True), (11, 'conduct', False),
        (12, 'emotional', False), (13, 'peer', True), (14, 'hyperactivity', False), 
        (15, 'emotional', False), (16, 'prosocial', False), (17, 'conduct', False), 
        (18, 'peer', False), (19, 'prosocial', False), (20, 'hyperactivity', True), 
        (21, 'conduct', False), (22, 'peer', False), (23, 'emotional', False), 
        (24, 'hyperactivity', True)
    ]
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SdqScoringService, cls).__new__(cls)
        return cls._instance

    def calculate_scores(self, answers: List[int]) -> dict:
        if len(answers) != 25:
            raise ValueError("Jawaban harus berisi 25 integer.")

        scores = {'emotional': 0, 'conduct': 0, 'hyperactivity': 0, 'peer': 0, 'prosocial': 0}

        for index, scale, is_reversed in self.SCORING_MAP:
            answer = answers[index] # Jawaban adalah 0, 1, atau 2
            score_value = 0
            
            # Logika reverse scoring: 0 -> 2, 1 -> 1, 2 -> 0
            if is_reversed:
                if answer == 0: score_value = 2
                elif answer == 1: score_value = 1
                # else: score_value = 0 (default)
            else:
                score_value = answer
            
            if scale in scores:
                scores[scale] += score_value

        # Total difficulties score adalah penjumlahan 4 skala masalah
        total_difficulties = scores['emotional'] + scores['conduct'] + scores['hyperactivity'] + scores['peer']
        scores['total_difficulties_score'] = total_difficulties
        
        return scores
    
sdq_scorer = SdqScoringService()