# insta2_final_fixed.py
"""
Instagram Bot Professional - Version 4.0
نظام تسجيل دخول احترافي متعدد المحاولات
"""

import os
import sys
import json
import time
import uuid
import random
import logging
import threading
import hashlib
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import deque
from queue import Queue, Empty
from requests.exceptions import HTTPError, ConnectionError, Timeout

# Import instagrapi with error handling
try:
    from instagrapi import Client
    from instagrapi.exceptions import (
        LoginRequired, ChallengeRequired, PleaseWaitFewMinutes,
        ClientLoginRequired, ClientError, RateLimitError
    )
except ImportError as e:
    print(f"❌ Failed to import instagrapi: {e}")
    print("📦 Please install: pip install instagrapi")
    sys.exit(1)

from groq import Groq
from dotenv import load_dotenv
from flask import Flask, jsonify, request, render_template_string

load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class Config:
    """Application configuration"""
    username: str = os.getenv("INSTAGRAM_USERNAME", "")
    password: str = os.getenv("INSTAGRAM_PASSWORD", "")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    
    session_file: str = "session.json"
    log_file: str = "bot.log"
    menu_file: str = "menu_config.json"
    
    # Session settings
    max_login_attempts: int = 5
    login_retry_delay: int = 5
    session_check_interval: int = 3
    
    # Rate limiting
    max_messages_per_hour: int = 50
    min_delay_between_messages: float = 3.0
    max_delay_between_messages: float = 6.0
    poll_interval: float = 15.0
    
    # Device settings
    device_country: str = "IQ"
    device_locale: str = "ar_AR"
    device_timezone_offset: int = 10800


# ============================================================================
# LOGGING SYSTEM
# ============================================================================

class Logger:
    """Professional logging system"""
    
    def __init__(self, log_file: str = "bot.log"):
        self.logger = logging.getLogger("InstagramBot")
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()
        
        try:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
        except Exception as e:
            print(f"⚠️ Logging setup error: {e}")
    
    def debug(self, msg: str): self.logger.debug(msg)
    def info(self, msg: str): self.logger.info(msg)
    def warning(self, msg: str): self.logger.warning(msg)
    def error(self, msg: str): self.logger.error(msg)
    def critical(self, msg: str): self.logger.critical(msg)


# ============================================================================
# DEVICE MANAGER
# ============================================================================

@dataclass
class DeviceFingerprint:
    """Device fingerprint for consistent session"""
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))
    phone_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    device_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    advertising_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    country: str = "IQ"
    locale: str = "ar_AR"
    timezone_offset: int = 10800


class DeviceManager:
    """Manages device fingerprint"""
    
    def __init__(self, session_file: str = "session.json"):
        self.session_file = session_file
        self.device = self._load_or_create_device()
    
    def _load_or_create_device(self) -> DeviceFingerprint:
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'device' in data:
                        d = data['device']
                        return DeviceFingerprint(
                            uuid=d.get('uuid', str(uuid.uuid4())),
                            phone_id=d.get('phone_id', str(uuid.uuid4())),
                            device_id=d.get('device_id', str(uuid.uuid4())),
                            advertising_id=d.get('advertising_id', str(uuid.uuid4())),
                            user_agent=d.get('user_agent', DeviceFingerprint().user_agent),
                            country=d.get('country', 'IQ'),
                            locale=d.get('locale', 'ar_AR'),
                            timezone_offset=d.get('timezone_offset', 10800)
                        )
        except:
            pass
        return DeviceFingerprint()
    
    def apply_to_client(self, client: Client):
        try:
            client.set_user_agent(self.device.user_agent)
            client.set_country(self.device.country)
            client.set_locale(self.device.locale)
            client.set_timezone_offset(self.device.timezone_offset)
            
            if hasattr(client, 'set_uuid'):
                client.set_uuid(self.device.uuid)
            if hasattr(client, 'set_phone_id'):
                client.set_phone_id(self.device.phone_id)
            if hasattr(client, 'set_device_id'):
                client.set_device_id(self.device.device_id)
            if hasattr(client, 'set_advertising_id'):
                client.set_advertising_id(self.device.advertising_id)
        except:
            pass
    
    def save(self, client: Client):
        try:
            data = {}
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            data['device'] = {
                'uuid': self.device.uuid,
                'phone_id': self.device.phone_id,
                'device_id': self.device.device_id,
                'advertising_id': self.device.advertising_id,
                'user_agent': self.device.user_agent,
                'country': self.device.country,
                'locale': self.device.locale,
                'timezone_offset': self.device.timezone_offset
            }
            
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            pass


# ============================================================================
# PROFESSIONAL SESSION MANAGER
# ============================================================================

class SessionManager:
    """Professional session management with multiple login strategies"""
    
    def __init__(self, logger: Logger, device_manager: DeviceManager, config: Config):
        self.logger = logger
        self.device_manager = device_manager
        self.config = config
        self.client = None
        self.is_logged_in = False
        self._login_lock = threading.Lock()
        self._login_attempts = 0
        self._last_login_attempt = 0
        self._session_valid = False
    
    def create_new_client(self) -> Client:
        """Create a fresh client instance"""
        client = Client()
        self.device_manager.apply_to_client(client)
        return client
    
    def _clean_session_file(self):
        """Remove corrupted session file"""
        try:
            if os.path.exists(self.config.session_file):
                os.remove(self.config.session_file)
                self.logger.info("🗑️ Corrupted session file removed")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not remove session file: {e}")
    
    def _attempt_login_with_retry(self, max_attempts: int = 5) -> bool:
        """Attempt login with multiple retries and different strategies"""
        
        strategies = [
            # Strategy 1: Fresh login with new client
            lambda: self._login_fresh(),
            
            # Strategy 2: Try with loaded settings if exists
            lambda: self._login_with_settings(),
            
            # Strategy 3: Force new login with clean client
            lambda: self._login_force_new(),
        ]
        
        for attempt in range(max_attempts):
            self._login_attempts += 1
            self._last_login_attempt = time.time()
            
            self.logger.info(f"🔄 Login attempt {attempt + 1}/{max_attempts}")
            
            for strategy_idx, strategy in enumerate(strategies):
                try:
                    self.logger.debug(f"  📌 Trying strategy {strategy_idx + 1}")
                    if strategy():
                        self.is_logged_in = True
                        self._session_valid = True
                        self._login_attempts = 0
                        return True
                except ChallengeRequired:
                    self.logger.error("⚠️ Challenge required! Please verify in Instagram app")
                    return False
                except PleaseWaitFewMinutes:
                    wait_time = 120 + random.randint(0, 60)
                    self.logger.warning(f"⏳ Please wait {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                except Exception as e:
                    self.logger.warning(f"  ⚠️ Strategy {strategy_idx + 1} failed: {str(e)[:50]}")
                    time.sleep(self.config.login_retry_delay)
                    continue
            
            # If all strategies failed, wait before next attempt
            if attempt < max_attempts - 1:
                wait = self.config.login_retry_delay * (attempt + 1)
                self.logger.info(f"⏳ Waiting {wait} seconds before next attempt...")
                time.sleep(wait)
        
        return False
    
    def _login_fresh(self) -> bool:
        """Fresh login with new client"""
        try:
            self.client = self.create_new_client()
            self.logger.info(f"🔐 Logging in as {self.config.username}...")
            self.client.login(self.config.username, self.config.password)
            self.client.dump_settings(self.config.session_file)
            self.device_manager.save(self.client)
            self.logger.info(f"✅ Login successful: @{self.client.username}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Fresh login failed: {e}")
            return False
    
    def _login_with_settings(self) -> bool:
        """Try loading existing session settings"""
        try:
            if not os.path.exists(self.config.session_file):
                return False
            
            self.client = self.create_new_client()
            self.client.load_settings(self.config.session_file)
            
            # Verify session is valid
            self.client.get_timeline_feed()
            self.logger.info("✅ Session loaded and verified")
            return True
        except LoginRequired:
            self.logger.warning("⚠️ Session expired, removing...")
            self._clean_session_file()
            return False
        except Exception as e:
            self.logger.warning(f"⚠️ Session load failed: {e}")
            return False
    
    def _login_force_new(self) -> bool:
        """Force new login with clean client and no cache"""
        try:
            # Clean everything
            self._clean_session_file()
            self.client = self.create_new_client()
            
            # Try with different user agent
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
            ]
            self.client.set_user_agent(random.choice(user_agents))
            
            self.logger.info("🔐 Force login with new identity...")
            self.client.login(self.config.username, self.config.password)
            self.client.dump_settings(self.config.session_file)
            self.device_manager.save(self.client)
            self.logger.info("✅ Force login successful")
            return True
        except Exception as e:
            self.logger.error(f"❌ Force login failed: {e}")
            return False
    
    def login(self) -> bool:
        """Main login method with full retry system"""
        with self._login_lock:
            self.logger.info("="*50)
            self.logger.info("🔐 Starting login process...")
            
            # Check if already logged in
            if self.is_logged_in and self.client:
                try:
                    self.client.get_timeline_feed()
                    self.logger.info("✅ Already logged in")
                    return True
                except:
                    self.is_logged_in = False
            
            # Attempt login with retry
            success = self._attempt_login_with_retry(self.config.max_login_attempts)
            
            if success:
                self.logger.info("="*50)
                self.logger.info(f"✅ Successfully logged in as @{self.client.username}")
                self.logger.info("="*50)
                return True
            else:
                self.logger.error("="*50)
                self.logger.error("❌ All login attempts failed")
                self.logger.error("💡 Possible solutions:")
                self.logger.error("   1. Check username/password in .env")
                self.logger.error("   2. Open Instagram and complete any verification")
                self.logger.error("   3. Wait a few minutes and try again")
                self.logger.error("   4. Delete session.json and try again")
                self.logger.error("="*50)
                return False
    
    def check_session(self) -> bool:
        """Check if current session is valid"""
        if not self.client or not self.is_logged_in:
            return False
        
        try:
            self.client.get_timeline_feed()
            return True
        except LoginRequired:
            self.logger.warning("⚠️ Session expired")
            self.is_logged_in = False
            self._session_valid = False
            return False
        except Exception:
            return False
    
    def get_client(self) -> Optional[Client]:
        """Get valid client, re-login if needed"""
        if not self.is_logged_in or not self.client:
            if not self.login():
                return None
        
        if not self.check_session():
            self.logger.warning("⚠️ Session invalid, re-logging...")
            if not self.login():
                return None
        
        return self.client
    
    def logout(self):
        """Logout and cleanup"""
        try:
            if self.client:
                self.client.logout()
        except:
            pass
        self.client = None
        self.is_logged_in = False
        self._session_valid = False
        self.logger.info("👋 Logged out")


# ============================================================================
# RATE LIMITER
# ============================================================================

class RateLimiter:
    """Rate limiter with adaptive delays"""
    
    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self.logger = logger
        self.message_timestamps = deque(maxlen=100)
        self.cooldown_until = 0
        self._lock = threading.Lock()
        self._hourly_count = 0
        self._hourly_reset = time.time() + 3600
    
    def wait(self, force_delay: bool = True):
        with self._lock:
            now = time.time()
            
            if now < self.cooldown_until:
                wait_time = self.cooldown_until - now + 1
                self.logger.warning(f"⏳ Cooldown: {wait_time:.0f}s")
                time.sleep(wait_time)
                self.cooldown_until = 0
            
            if now > self._hourly_reset:
                self._hourly_count = 0
                self._hourly_reset = now + 3600
            
            if self._hourly_count >= self.config.max_messages_per_hour:
                wait_time = self._hourly_reset - now + 5
                self.logger.warning(f"⏳ Hourly limit: {wait_time:.0f}s")
                time.sleep(wait_time)
                self._hourly_count = 0
                self._hourly_reset = time.time() + 3600
            
            if force_delay:
                delay = random.uniform(
                    self.config.min_delay_between_messages,
                    self.config.max_delay_between_messages
                )
                time.sleep(delay)
    
    def record_message(self):
        with self._lock:
            self.message_timestamps.append(time.time())
            self._hourly_count += 1
    
    def set_cooldown(self, seconds: int = 300):
        with self._lock:
            self.cooldown_until = time.time() + seconds
            self.logger.warning(f"🔥 Cooldown: {seconds}s")


# ============================================================================
# REQUEST QUEUE
# ============================================================================

class RequestQueue:
    def __init__(self, logger: Logger, rate_limiter: RateLimiter):
        self.logger = logger
        self.rate_limiter = rate_limiter
        self.queue: Queue = Queue()
        self.is_processing = False
        self._process_thread = None
        self._stop_requested = False
    
    def add(self, func, *args, **kwargs):
        self.queue.put((func, args, kwargs))
        self._start_processing()
    
    def _start_processing(self):
        if not self.is_processing and not self._stop_requested:
            self.is_processing = True
            self._process_thread = threading.Thread(target=self._process_queue, daemon=True)
            self._process_thread.start()
    
    def _process_queue(self):
        while not self._stop_requested:
            try:
                func, args, kwargs = self.queue.get(timeout=1)
                if func:
                    self.rate_limiter.wait(force_delay=True)
                    try:
                        result = func(*args, **kwargs)
                        self.rate_limiter.record_message()
                    except Exception as e:
                        self.logger.error(f"❌ Queue request failed: {e}")
            except Empty:
                if not self.queue.empty():
                    continue
                self.is_processing = False
                break
            except Exception as e:
                self.logger.error(f"❌ Queue error: {e}")
                time.sleep(1)
    
    def stop(self):
        self._stop_requested = True
        self.is_processing = False


# ============================================================================
# AI MANAGER
# ============================================================================

class AIManager:
    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self.logger = logger
        self.client = None
        if config.groq_api_key:
            try:
                self.client = Groq(api_key=config.groq_api_key)
                self.logger.info("✅ Groq AI initialized")
            except Exception as e:
                self.logger.error(f"❌ Groq init failed: {e}")
    
    def get_response(self, message: str, username: str, personality: str, model: str) -> str:
        if not self.client:
            return "عذراً، خدمة الذكاء الاصطناعي غير متاحة حالياً 🙏"
        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": personality},
                    {"role": "user", "content": f"@{username}: {message}"}
                ],
                max_tokens=250,
                temperature=0.7,
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            self.logger.error(f"❌ AI error: {e}")
            return "عذراً، حدث خطأ مؤقت. حاول مرة أخرى 🙏"


# ============================================================================
# MENU MANAGER
# ============================================================================

class MenuManager:
    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self.logger = logger
        self._menu = self._load_menu()
    
    def _load_menu(self) -> dict:
        default_menu = {
            "owner": {
                "name": "السيد أبو راشد",
                "title": "مبرمج شغوف ومبتكر",
                "bio": "يسعى للأفضل دائماً",
                "dua": "اللهم اغفر لوالديّ وارحمهما",
                "whatsapp": "+964XXXXXXXXX",
                "telegram": "@AbuRashid"
            },
            "projects": [
                {"id": 1, "name": "منصة البروفسور التعليمية", "emoji": "📚",
                 "description": "منصة تعليمية متكاملة", "link": "https://example.com/professor"},
                {"id": 2, "name": "تطبيق الراية للقرآن", "emoji": "📖",
                 "description": "تطبيق لقراءة القرآن", "link": "https://example.com/raya"},
                {"id": 3, "name": "متجر أنا وإياك", "emoji": "☕",
                 "description": "متجر إلكتروني لكافيه", "link": "https://example.com/anawayyak"},
                {"id": 4, "name": "نظام مجمع الحسيين", "emoji": "🏪",
                 "description": "نظام إدارة متجر", "link": "https://example.com/hussain"},
                {"id": 5, "name": "تطبيق GeoLock", "emoji": "📍",
                 "description": "تطبيق للتحكم الجغرافي", "link": "https://example.com/geolock"}
            ],
            "ai_personality": "أنت مساعد ذكي ودود يمثّل المبرمج أبو راشد على إنستغرام. تحدث بالعربية دائماً، كن مختصراً ومفيداً.",
            "groq_model": "llama-3.3-70b-versatile"
        }
        
        try:
            if os.path.exists(self.config.menu_file):
                with open(self.config.menu_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key in default_menu:
                        if key not in data:
                            data[key] = default_menu[key]
                    return data
        except Exception as e:
            self.logger.error(f"❌ Menu load error: {e}")
        
        self.save(default_menu)
        return default_menu
    
    def save(self, data: dict = None):
        try:
            if data:
                self._menu = data
            with open(self.config.menu_file, 'w', encoding='utf-8') as f:
                json.dump(self._menu, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"❌ Menu save error: {e}")
    
    def get_owner(self) -> dict:
        return self._menu.get("owner", {})
    
    def get_projects(self) -> list:
        return self._menu.get("projects", [])
    
    def get_project(self, project_id: int) -> Optional[dict]:
        return next((p for p in self.get_projects() if p.get("id") == project_id), None)
    
    def get_ai_personality(self) -> str:
        return self._menu.get("ai_personality", "")
    
    def get_groq_model(self) -> str:
        return self._menu.get("groq_model", "llama-3.3-70b-versatile")
    
    def create_main_menu(self, username: str) -> str:
        name = self.get_owner().get("name", "أبو راشد")
        return f"""👋 أهلاً وسهلاً @{username}!

أنا {name}، مساعدك الذكي ✨

┏━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃       📌 القائمة         ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  [1]  من أنا؟            ┃
┃  [2]  مشاريعي 🚀         ┃
┃  [3]  تواصل معي 📬       ┃
┃  [4]  اسألني 🤖          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━┛

✏️ أرسل رقم الاختيار أو سؤالك"""
    
    def create_projects_menu(self) -> str:
        menu = "🚀 مشاريعي\n┏━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n┃    قائمة المشاريع        ┃"
        for p in self.get_projects():
            menu += f"\n┃  [{p['id']}]  {p['emoji']} {p['name']}"
        menu += "\n┣━━━━━━━━━━━━━━━━━━━━━━━━━━┫\n┃  ↩️ اكتب (رجوع) للقائمة\n┗━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
        return menu
    
    def create_about_menu(self) -> str:
        o = self.get_owner()
        return f"""👨‍💻 {o.get('name', 'أبو راشد')}
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  💡 {o.get('title', 'مبرمج')}
┃  📝 {o.get('bio', '')}
┃  🤲 {o.get('dua', '')}
┣━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  ↩️ اكتب (رجوع) للقائمة
┗━━━━━━━━━━━━━━━━━━━━━━━━━━┛"""
    
    def create_contact_menu(self) -> str:
        o = self.get_owner()
        return f"""📬 تواصل مع {o.get('name', 'أبو راشد')}
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  💬 واتساب: {o.get('whatsapp', 'غير متاح')}
┃  ✈️ تيليغرام: {o.get('telegram', 'غير متاح')}
┣━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  ↩️ اكتب (رجوع) للقائمة
┗━━━━━━━━━━━━━━━━━━━━━━━━━━┛"""
    
    def create_ai_menu(self) -> str:
        return """🤖 وضع الدردشة الذكية
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  اطرح سؤالك وسأجيبك!
┣━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  ↩️ اكتب (رجوع) للقائمة
┗━━━━━━━━━━━━━━━━━━━━━━━━━━┛"""
    
    def create_project_detail(self, project_id: int) -> str:
        p = self.get_project(project_id)
        if not p:
            return "❌ مشروع غير موجود\n↩️ اكتب (مشاريع) للقائمة"
        return f"""{p['emoji']} {p['name']}
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  📋 {p['description']}
┃  🔗 {p['link']}
┣━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃  ↩️ اكتب (رجوع) للقائمة
┗━━━━━━━━━━━━━━━━━━━━━━━━━━┛"""


# ============================================================================
# USER STATE MANAGER
# ============================================================================

class UserStateManager:
    def __init__(self):
        self.users: Dict[str, dict] = {}
        self._lock = threading.Lock()
    
    def get_user(self, user_id: str) -> dict:
        with self._lock:
            if user_id not in self.users:
                self.users[user_id] = {"state": "main", "last_msg_id": None, "first": True}
            return self.users[user_id]
    
    def update_state(self, user_id: str, state: str):
        with self._lock:
            if user_id in self.users:
                self.users[user_id]["state"] = state
    
    def is_first_message(self, user_id: str) -> bool:
        with self._lock:
            return self.users.get(user_id, {}).get("first", True)
    
    def mark_not_first(self, user_id: str):
        with self._lock:
            if user_id in self.users:
                self.users[user_id]["first"] = False


# ============================================================================
# MESSAGE HANDLER
# ============================================================================

class MessageHandler:
    BACK_WORDS = {"رجوع", "back", "قائمة", "menu", "رئيسية"}
    
    def __init__(self, logger: Logger, menu_manager: MenuManager, ai_manager: AIManager, rate_limiter: RateLimiter):
        self.logger = logger
        self.menu_manager = menu_manager
        self.ai_manager = ai_manager
        self.rate_limiter = rate_limiter
        self.user_manager = UserStateManager()
    
    def send_message(self, client: Client, text: str, thread_id: str, retry: int = 0) -> bool:
        if not text or not thread_id:
            return False
        
        if len(text) > 900:
            text = text[:900] + "..."
        
        try:
            self.rate_limiter.wait(force_delay=True)
            client.direct_send(text, thread_ids=[thread_id])
            self.rate_limiter.record_message()
            return True
        except LoginRequired:
            if retry < 2:
                time.sleep(3)
                return self.send_message(client, text, thread_id, retry + 1)
        except Exception as e:
            if "1545003" in str(e):
                self.rate_limiter.set_cooldown(120)
                if retry < 2:
                    time.sleep(30)
                    return self.send_message(client, text, thread_id, retry + 1)
        return False
    
    def process_message(self, client: Client, sender_id: str, username: str, text: str, thread_id: str):
        text = text.strip()
        text_lower = text.lower()
        user = self.user_manager.get_user(sender_id)
        
        if len(text) < 1:
            return
        
        if text_lower in self.BACK_WORDS:
            self.user_manager.update_state(sender_id, "main")
            self.send_message(client, self.menu_manager.create_main_menu(username), thread_id)
            return
        
        if text_lower in {"مشاريع", "projects"}:
            self.user_manager.update_state(sender_id, "projects")
            self.send_message(client, self.menu_manager.create_projects_menu(), thread_id)
            return
        
        if text_lower in {"من انت", "من أنت", "من انا", "من أنا"}:
            self.user_manager.update_state(sender_id, "about")
            self.send_message(client, self.menu_manager.create_about_menu(), thread_id)
            return
        
        if text_lower in {"تواصل", "contact", "واتساب", "تيليغرام"}:
            self.user_manager.update_state(sender_id, "contact")
            self.send_message(client, self.menu_manager.create_contact_menu(), thread_id)
            return
        
        if self.user_manager.is_first_message(sender_id):
            self.user_manager.mark_not_first(sender_id)
            self.user_manager.update_state(sender_id, "main")
            self.send_message(client, self.menu_manager.create_main_menu(username), thread_id)
            return
        
        # Clean Arabic numbers
        clean_text = text
        for a, b in [("٠", "0"), ("١", "1"), ("٢", "2"), ("٣", "3"), ("٤", "4"),
                     ("٥", "5"), ("٦", "6"), ("٧", "7"), ("٨", "8"), ("٩", "9")]:
            clean_text = clean_text.replace(a, b)
        
        state = user.get("state", "main")
        
        if state == "main":
            if clean_text == "1":
                self.user_manager.update_state(sender_id, "about")
                self.send_message(client, self.menu_manager.create_about_menu(), thread_id)
            elif clean_text == "2":
                self.user_manager.update_state(sender_id, "projects")
                self.send_message(client, self.menu_manager.create_projects_menu(), thread_id)
            elif clean_text == "3":
                self.user_manager.update_state(sender_id, "contact")
                self.send_message(client, self.menu_manager.create_contact_menu(), thread_id)
            elif clean_text == "4":
                self.user_manager.update_state(sender_id, "ai")
                self.send_message(client, self.menu_manager.create_ai_menu(), thread_id)
            else:
                personality = self.menu_manager.get_ai_personality()
                model = self.menu_manager.get_groq_model()
                response = self.ai_manager.get_response(text, username, personality, model)
                self.send_message(client, f"{response}\n\n↩️ اكتب (رجوع) للقائمة", thread_id)
            return
        
        if state == "projects":
            if clean_text.isdigit():
                project_id = int(clean_text)
                if self.menu_manager.get_project(project_id):
                    self.send_message(client, self.menu_manager.create_project_detail(project_id), thread_id)
                else:
                    self.send_message(client, self.menu_manager.create_projects_menu(), thread_id)
            else:
                self.send_message(client, self.menu_manager.create_projects_menu(), thread_id)
            return
        
        if state == "ai":
            personality = self.menu_manager.get_ai_personality()
            model = self.menu_manager.get_groq_model()
            response = self.ai_manager.get_response(text, username, personality, model)
            self.send_message(client, f"{response}\n\n↩️ اكتب (رجوع) للقائمة", thread_id)
            return
        
        self.user_manager.update_state(sender_id, "main")
        self.send_message(client, self.menu_manager.create_main_menu(username), thread_id)


# ============================================================================
# POLLING MANAGER
# ============================================================================

class PollingManager:
    def __init__(self, logger: Logger, config: Config):
        self.logger = logger
        self.config = config
        self.last_msg_ids: Dict[str, str] = {}
        self._running = False
        self._poll_thread = None
        self.user_cache: Dict[str, Tuple[str, float]] = {}
        self.cache_ttl = 300
    
    def _get_username(self, client: Client, user_id: str) -> str:
        now = time.time()
        if user_id in self.user_cache:
            username, timestamp = self.user_cache[user_id]
            if now - timestamp < self.cache_ttl:
                return username
        
        try:
            info = client.user_info(int(user_id))
            username = info.username
            self.user_cache[user_id] = (username, now)
            return username
        except:
            return user_id
    
    def start(self, client: Client, message_handler, config: Config):
        if self._running:
            return
        
        self._running = True
        self._poll_thread = threading.Thread(
            target=self._poll_loop,
            args=(client, message_handler, config),
            daemon=True
        )
        self._poll_thread.start()
        self.logger.info("🔍 Polling started")
    
    def stop(self):
        self._running = False
        if self._poll_thread:
            self._poll_thread.join(timeout=5)
        self.logger.info("⏹️ Polling stopped")
    
    def _poll_loop(self, client: Client, message_handler, config: Config):
        consecutive_errors = 0
        
        while self._running:
            try:
                threads = client.direct_threads(amount=5)
                consecutive_errors = 0
                
                for thread in threads:
                    if not thread.messages:
                        continue
                    
                    msg = thread.messages[0]
                    sender_id = str(msg.user_id)
                    
                    if sender_id == str(client.user_id):
                        continue
                    if msg.item_type != "text":
                        continue
                    if not msg.text:
                        continue
                    
                    msg_id = str(msg.id)
                    thread_id = str(thread.id)
                    
                    if thread_id in self.last_msg_ids and self.last_msg_ids[thread_id] == msg_id:
                        continue
                    
                    self.last_msg_ids[thread_id] = msg_id
                    username = self._get_username(client, sender_id)
                    
                    self.logger.info(f"📨 @{username}: {msg.text[:50]}")
                    message_handler.process_message(client, sender_id, username, msg.text, thread_id)
                
                time.sleep(random.uniform(
                    config.poll_interval * 0.8,
                    config.poll_interval * 1.2
                ))
                
            except LoginRequired:
                self.logger.warning("⚠️ Login required in polling")
                break
            except Exception as e:
                consecutive_errors += 1
                self.logger.error(f"⚠️ Polling error: {e}")
                if consecutive_errors > 5:
                    break
                time.sleep(min(60, 5 * consecutive_errors))


# ============================================================================
# DASHBOARD
# ============================================================================

class DashboardManager:
    def __init__(self, logger: Logger, menu_manager: MenuManager):
        self.logger = logger
        self.menu_manager = menu_manager
        self.app = None
        self.thread = None
        self._running = False
    
    def start(self):
        if self._running:
            return
        
        self._running = True
        self._create_app()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.logger.info("🌐 Dashboard on http://localhost:5000")
    
    def stop(self):
        self._running = False
    
    def _create_app(self):
        app = Flask(__name__)
        
        HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>بوت أبو راشد</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#07070f;color:#eeeef8;font-family:'Cairo',sans-serif}
h1{text-align:center;padding:30px;color:#7c6fff}
.card{background:#0f0f1a;border:1px solid #252540;border-radius:16px;padding:24px;margin:16px auto;max-width:800px}
input,textarea{width:100%;background:#07070f;border:1.5px solid #252540;border-radius:9px;padding:11px;color:#eeeef8;margin-bottom:16px}
button{background:#7c6fff;color:#fff;padding:10px 20px;border:none;border-radius:9px;cursor:pointer}
</style>
</head>
<body>
<h1>🤖 بوت أبو راشد</h1>
<div class="card"><h2>✏️ إعدادات البوت</h2>
<div id="status">🟢 البوت يعمل</div>
</div>
</body>
</html>"""
        
        @app.route('/')
        def index():
            return render_template_string(HTML_TEMPLATE)
        
        @app.route('/api/config', methods=['GET'])
        def get_config():
            return jsonify(self.menu_manager._menu)
        
        @app.route('/api/config', methods=['POST'])
        def update_config():
            data = request.get_json()
            if data:
                self.menu_manager._menu.update(data)
                self.menu_manager.save()
            return jsonify({"ok": True})
        
        self.app = app
    
    def _run(self):
        try:
            self.app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
        except Exception as e:
            self.logger.error(f"❌ Dashboard error: {e}")


# ============================================================================
# MAIN APPLICATION
# ============================================================================

class InstagramBot:
    def __init__(self):
        self.config = Config()
        self.logger = Logger(self.config.log_file)
        self.device_manager = DeviceManager(self.config.session_file)
        self.session_manager = SessionManager(self.logger, self.device_manager, self.config)
        self.rate_limiter = RateLimiter(self.config, self.logger)
        self.request_queue = RequestQueue(self.logger, self.rate_limiter)
        self.menu_manager = MenuManager(self.config, self.logger)
        self.ai_manager = AIManager(self.config, self.logger)
        self.message_handler = MessageHandler(self.logger, self.menu_manager, self.ai_manager, self.rate_limiter)
        self.dashboard = DashboardManager(self.logger, self.menu_manager)
        self.polling_manager = PollingManager(self.logger, self.config)
        self._running = False
        
        self.logger.info("🚀 Bot initialized")
    
    def start(self):
        self.logger.info("="*55)
        self.logger.info("  🤖  Instagram Bot Professional v4.0")
        self.logger.info("  ⚡  Powered by Groq + Llama 3.3 70B")
        self.logger.info("="*55)
        
        if not self.session_manager.login():
            self.logger.error("❌ Login failed")
            return
        
        self.logger.info(f"  👤  Account: @{self.session_manager.client.username}")
        
        self.dashboard.start()
        
        client = self.session_manager.get_client()
        if not client:
            self.logger.error("❌ No valid client")
            return
        
        self._running = True
        self.polling_manager.start(client, self.message_handler, self.config)
        
        self.logger.info("✅ Bot running. Press CTRL+C to stop")
        
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("\n🛑 Stopping...")
        finally:
            self.stop()
    
    def stop(self):
        self._running = False
        self.polling_manager.stop()
        self.dashboard.stop()
        self.session_manager.logout()
        self.logger.info("👋 Bot stopped")


if __name__ == "__main__":
    bot = InstagramBot()
    bot.start()
    
