from typing import Dict, Any

class InterpretationService:
    _instance = None
    
    # Ambang Batas (Cutoff Points) - Nilai maksimal untuk Normal dan Borderline
    CUTOFF_POINTS = {
        'emotional': {'normal_max': 3, 'borderline_max': 6},
        'conduct': {'normal_max': 3, 'borderline_max': 5},
        'hyperactivity': {'normal_max': 5, 'borderline_max': 7},
        'peer': {'normal_max': 3, 'borderline_max': 5},
        'total': {'normal_max': 13, 'borderline_max': 16}
    }

    INTERPRETATION_TEXTS = {
        'total': {
            'normal': {
                "title": "Gambaran Umum: Sebagian Besar Baik",
                "description": "Secara umum, anak Anda menunjukkan perkembangan yang baik di berbagai area. Ini adalah fondasi yang kuat. Teruslah memberikan dukungan dan cinta yang telah Anda berikan.",
                "advice": "Pertahankan komunikasi yang terbuka dan perhatikan setiap perubahan kecil seiring waktu."
            },
            'borderline': {
                "title": "Gambaran Umum: Ada Beberapa Area yang Perlu Diperhatikan",
                "description": "Hasil ini menunjukkan ada beberapa area di mana anak Anda mungkin mengalami sedikit kesulitan. Ini sangat umum terjadi dan bukan berarti ada masalah besar. Ini adalah kesempatan baik untuk lebih memahami apa yang ia rasakan.",
                "advice": "Fokus pada area yang ditandai di bawah ini. Coba ajak anak berbicara santai tentang harinya di sekolah atau dengan teman-temannya."
            },
            'abnormal': {
                "title": "Gambaran Umum: Saatnya Memberi Perhatian Lebih",
                "description": "Beberapa area menunjukkan bahwa anak Anda mungkin sedang menghadapi tantangan yang cukup signifikan. Jangan panik, ini adalah sinyal penting bagi Anda untuk mendekat dan memberikan dukungan ekstra. Anda telah mengambil langkah pertama yang hebat dengan melakukan skrining ini.",
                "advice": "Sangat disarankan untuk berbicara lebih dalam dengan anak Anda, guru di sekolah, atau mempertimbangkan untuk berkonsultasi dengan psikolog anak untuk mendapatkan panduan lebih lanjut."
            }
        },
        'emotional': {
            "title": "Gejala Emosional (Kekhawatiran & Kesedihan)",
            "normal": "Anak Anda tampak cukup stabil secara emosional dan mampu mengelola perasaannya dengan baik.",
            "borderline": "Anak Anda menunjukkan beberapa tanda kekhawatiran atau kesedihan yang sedikit lebih sering dari biasanya. Coba perhatikan apakah ada pemicu tertentu.",
            "abnormal": "Tingkat kekhawatiran, kesedihan, atau keluhan fisik (seperti sakit kepala) cukup tinggi. Ini bisa menjadi tanda ia sedang tertekan atau cemas, mungkin karena tekanan di sekolah atau lingkungan pertemanan."
        },
        'conduct': {
            "title": "Masalah Perilaku (Temperamen & Kepatuhan)",
            "normal": "Anak Anda umumnya patuh dan dapat mengelola emosi marahnya dengan baik.",
            "borderline": "Terkadang anak Anda mungkin menunjukkan sifat lekas marah atau sulit diatur. Perhatikan situasi apa yang biasanya memicu perilaku ini.",
            "abnormal": "Anak Anda sering menunjukkan perilaku menentang, mudah marah, atau bertengkar. Ini bisa jadi cara ia mengekspresikan frustrasi atau kesulitan yang tidak bisa ia utarakan."
        },
        'hyperactivity': {
            "title": "Hiperaktivitas & Konsentrasi",
            "normal": "Anak Anda memiliki tingkat energi dan konsentrasi yang sesuai dengan usianya.",
            "borderline": "Anak Anda mungkin sedikit lebih aktif dari teman sebayanya atau kadang sulit fokus. Ini bisa jadi normal, namun tetap baik untuk diamati.",
            "abnormal": "Anak Anda menunjukkan kesulitan yang signifikan untuk tetap tenang, fokus, dan menyelesaikan tugas. Ini dapat memengaruhi performa akademis dan interaksi sosialnya."
        },
        'peer': {
            "title": "Masalah Hubungan Teman Sebaya",
            "normal": "Anak Anda tampaknya memiliki hubungan yang baik dengan teman-temannya.",
            "borderline": "Anak Anda mungkin mengalami sedikit kesulitan dalam berinteraksi, seperti lebih suka menyendiri atau sulit akrab. Ini bisa menjadi tanda awal masalah sosial.",
            "abnormal": "Anak Anda menunjukkan kesulitan yang jelas dalam hubungan pertemanan, seperti tidak punya teman baik, sering diganggu, atau lebih suka bergaul dengan orang dewasa. Ini adalah area yang sangat penting untuk diperhatikan, terutama dalam konteks perundungan (bullying)."
        },
         'prosocial': {
            "title": "Perilaku Prososial (Empati & Kepedulian)",
            "description": "Skor ini mengukur sejauh mana anak Anda peduli pada perasaan orang lain, suka menolong, dan berbagi. Skor yang tinggi di sini adalah pertanda yang sangat positif."
        }
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InterpretationService, cls).__new__(cls)
        return cls._instance

    def _get_level(self, scale_name: str, score: int) -> str:
        points = self.CUTOFF_POINTS.get(scale_name)
        if not points: return "normal"
        
        if score <= points['normal_max']: 
            return "normal"
        elif score <= points['borderline_max']: 
            return "borderline"
        else: 
            return "abnormal"

    def generate_full_interpretation(self, scores: Dict[str, Any]) -> Dict[str, Any]:
        total_score = scores.get('total_difficulties_score', 0)
        total_level = self._get_level('total', total_score)

        overall_summary = self.INTERPRETATION_TEXTS['total'][total_level]

        detailed_breakdown = []
        for scale in ['emotional', 'conduct', 'hyperactivity', 'peer']:
            score = scores.get(scale, 0)
            level = self._get_level(scale, score)
            scale_texts = self.INTERPRETATION_TEXTS[scale]
            detailed_breakdown.append({
                "scale": scale,
                "title": scale_texts['title'],
                "score": score,
                "level": level,
                "description": scale_texts[level]
            })

        prosocial_score = scores.get('prosocial', 0)
        detailed_breakdown.append({
            "scale": "prosocial",
            "title": self.INTERPRETATION_TEXTS['prosocial']['title'],
            "score": prosocial_score,
            "level": "info",
            "description": self.INTERPRETATION_TEXTS['prosocial']['description']
        })
        
        return {
            "total_score": total_score,
            "total_level": total_level,
            "overall_summary": overall_summary,
            "detailed_breakdown": detailed_breakdown
        }

interpreter = InterpretationService()