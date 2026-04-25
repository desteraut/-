"""
NLLBEngine — движок перевода на основе NLLB (Facebook)
"""

from .base_engine import BaseTranslationEngine
from config import SOURCE_LANGUAGE, TARGET_LANGUAGE, MODEL_CACHE_DIR, USE_GPU
import logging

logger = logging.getLogger(__name__)


class NLLBEngine(BaseTranslationEngine):
    """NLLB (No Language Left Behind) движок"""
    
    def __init__(self, source_lang: str = SOURCE_LANGUAGE, target_lang: str = TARGET_LANGUAGE):
        super().__init__(source_lang, target_lang)
        self.pipeline = None
        self.tokenizer = None
        self.device = "cpu"
    
    def _detect_device(self) -> str:
        """Определяет доступное устройство"""
        if not USE_GPU:
            return "cpu"
        try:
            import torch
            if torch.cuda.is_available():
                logger.info(f"✅ NVIDIA GPU: {torch.cuda.get_device_name(0)}")
                return "cuda"
            logger.warning("⚠️ GPU не найден, используется CPU")
            return "cpu"
        except:
            return "cpu"
    
    def initialize(self) -> bool:
        """Инициализация NLLB"""
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            import torch
            
            model_name = "facebook/nllb-200-distilled-600M"
            self.device = self._detect_device()
            
            logger.info(f"🔄 Загрузка NLLB ({self.device})...")
            MODEL_CACHE_DIR.mkdir(exist_ok=True)
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=str(MODEL_CACHE_DIR)
            )
            
            if self.device == "cuda":
                self.pipeline = AutoModelForSeq2SeqLM.from_pretrained(
                    model_name,
                    cache_dir=str(MODEL_CACHE_DIR),
                    torch_dtype=torch.float16,
                    device_map="auto"
                )
                logger.info("✅ NLLB на GPU!")
            else:
                self.pipeline = AutoModelForSeq2SeqLM.from_pretrained(
                    model_name,
                    cache_dir=str(MODEL_CACHE_DIR)
                )
                logger.info("✅ NLLB на CPU!")
            
            self.tokenizer.src_lang = "eng_Latn"
            self.target_lang_code = "rus_Cyrl"
            self.is_ready = True
            return True
            
        except Exception as e:
            logger.error(f"❌ NLLB ошибка: {e}")
            self.is_ready = False
            return False
    
    def translate(self, text: str) -> str:
        """Перевод через NLLB"""
        if not self.is_ready or not self.pipeline or not self.tokenizer:
            return text
        try:
            import torch
            self.tokenizer.src_lang = "eng_Latn"
            inputs = self.tokenizer(text, return_tensors="pt")
            
            if self.device == "cuda":
                inputs = {k: v.to("cuda") for k, v in inputs.items()}
            
            generated = self.pipeline.generate(
                **inputs,
                forced_bos_token_id=self.tokenizer.lang_code_to_id[self.target_lang_code],
                max_length=512,
                num_beams=4,
                early_stopping=True
            )
            return self.tokenizer.batch_decode(generated, skip_special_tokens=True)[0]
        except Exception as e:
            logger.error(f"NLLB error: {e}")
            return text
    
    def is_available(self) -> bool:
        """Проверка доступности"""
        return self.is_ready