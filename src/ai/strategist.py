"""
LLM Strategist System for Enemy AI
Provides tactical insights by querying LLM models when enemies can't find the player.
"""

import json
import time
import asyncio
import threading
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class StrategyRequest:
    """A request for strategic advice."""
    request_id: str
    player_tendencies: dict
    enemy_positions: List[Tuple[float, float]]
    last_known_player_pos: Optional[Tuple[int, int]]
    floor_number: int
    timestamp: float = field(default_factory=time.time)
    

@dataclass
class StrategyResponse:
    """Response from LLM strategist."""
    request_id: str
    suggested_positions: List[Tuple[int, int]]  # Where enemies should search
    suggested_formation: str  # "spread", "group", "ambush"
    reasoning: str  # Why this strategy
    confidence: float  # 0.0 to 1.0
    timestamp: float = field(default_factory=time.time)


class LLMProvider:
    """Abstract base for LLM providers."""
    
    def __init__(self, api_key: str = "", model: str = ""):
        self.api_key = api_key
        self.model = model
        self.enabled = bool(api_key)
    
    async def get_strategy(self, prompt: str) -> str:
        """Get strategic advice from the LLM."""
        raise NotImplementedError
        

class GeminiProvider(LLMProvider):
    """Google Gemini API provider."""
    
    def __init__(self, api_key: str = "", model: str = "gemini-2.0-flash"):
        super().__init__(api_key, model)
        
    async def get_strategy(self, prompt: str) -> str:
        """Query Gemini API."""
        if not self.enabled:
            return ""
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)
            response = await asyncio.to_thread(
                lambda: model.generate_content(prompt)
            )
            return response.text
        except Exception as e:
            print(f"[Strategist] Gemini error: {e}")
            return ""


class OpenAIProvider(LLMProvider):
    """OpenAI API provider."""
    
    def __init__(self, api_key: str = "", model: str = "gpt-4o-mini"):
        super().__init__(api_key, model)
        
    async def get_strategy(self, prompt: str) -> str:
        """Query OpenAI API."""
        if not self.enabled:
            return ""
        
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=self.api_key)
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a tactical AI advisor for enemy units in a stealth game. Provide concise, actionable advice."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[Strategist] OpenAI error: {e}")
            return ""


class OllamaProvider(LLMProvider):
    """Local Ollama provider."""
    
    def __init__(self, model: str = "llama3.2:3b", host: str = "http://localhost:11434"):
        super().__init__("local", model)
        self.host = host
        self.enabled = True  # Always try local
        
    async def get_strategy(self, prompt: str) -> str:
        """Query local Ollama."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.host}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"num_predict": 150}
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "")
        except Exception as e:
            # Ollama not running - this is expected
            pass
        return ""


class EnemyStrategist:
    """
    LLM-powered strategic advisor for enemy AI.
    
    When enemies lose track of the player, they can query this system
    for tactical advice based on player behavior patterns.
    """
    
    # Rate limiting
    MIN_REQUEST_INTERVAL = 5.0  # Seconds between LLM queries
    MAX_PENDING_REQUESTS = 3
    
    def __init__(self, settings_manager=None):
        self.settings_manager = settings_manager
        self.last_request_time = 0.0
        self.pending_requests: Dict[str, StrategyRequest] = {}
        self.cached_responses: Dict[str, StrategyResponse] = {}
        self.response_cache_duration = 30.0  # Seconds
        
        # Initialize providers (lazy - only when needed)
        self._providers: List[LLMProvider] = []
        self._providers_initialized = False
        
        # Background thread for async queries
        self._query_thread: Optional[threading.Thread] = None
        self._query_queue: List[StrategyRequest] = []
        self._response_queue: List[StrategyResponse] = []
        self._running = True
        
    def _init_providers(self):
        """Initialize LLM providers from settings."""
        if self._providers_initialized:
            return
        
        self._providers_initialized = True
        
        # Try to get API keys from settings or environment
        import os
        
        # Gemini
        gemini_key = os.environ.get("GEMINI_API_KEY", "")
        if self.settings_manager:
            gemini_key = self.settings_manager.get("ai", "gemini_api_key") or gemini_key
        if gemini_key:
            self._providers.append(GeminiProvider(gemini_key))
        
        # OpenAI
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        if self.settings_manager:
            openai_key = self.settings_manager.get("ai", "openai_api_key") or openai_key
        if openai_key:
            self._providers.append(OpenAIProvider(openai_key))
        
        # Local Ollama (always add as fallback)
        self._providers.append(OllamaProvider())
        
        print(f"[Strategist] Initialized {len(self._providers)} LLM providers")
    
    def request_strategy(self, game, enemies: list) -> Optional[str]:
        """
        Request strategic advice for enemies.
        
        Returns request_id if submitted, None if rate-limited or unavailable.
        """
        # Rate limiting
        current_time = time.time()
        if current_time - self.last_request_time < self.MIN_REQUEST_INTERVAL:
            return None
        
        if len(self.pending_requests) >= self.MAX_PENDING_REQUESTS:
            return None
        
        # Get player behavior data
        if not hasattr(game, 'behavior_tracker') or not game.behavior_tracker:
            return None
        
        tendencies = game.behavior_tracker.get_player_tendencies()
        
        # Create request
        request_id = f"req_{int(current_time * 1000)}"
        request = StrategyRequest(
            request_id=request_id,
            player_tendencies=tendencies,
            enemy_positions=[(e.x, e.y) for e in enemies if e.is_alive],
            last_known_player_pos=enemies[0].last_known_player_pos if enemies else None,
            floor_number=game.current_level_num
        )
        
        self.pending_requests[request_id] = request
        self.last_request_time = current_time
        
        # Queue for background processing
        self._query_queue.append(request)
        
        # Start background thread if not running
        if self._query_thread is None or not self._query_thread.is_alive():
            self._query_thread = threading.Thread(target=self._process_queries, daemon=True)
            self._query_thread.start()
        
        return request_id
    
    def get_response(self, request_id: str) -> Optional[StrategyResponse]:
        """
        Get response for a previous request.
        Returns None if not ready yet.
        """
        # Check cache first
        if request_id in self.cached_responses:
            response = self.cached_responses[request_id]
            if time.time() - response.timestamp < self.response_cache_duration:
                return response
        
        # Check response queue
        for response in self._response_queue:
            if response.request_id == request_id:
                self._response_queue.remove(response)
                self.cached_responses[request_id] = response
                self.pending_requests.pop(request_id, None)
                return response
        
        return None
    
    def _process_queries(self):
        """Background thread to process LLM queries."""
        self._init_providers()
        
        while self._running and self._query_queue:
            request = self._query_queue.pop(0)
            
            # Build prompt
            prompt = self._build_prompt(request)
            
            # Try each provider
            response_text = ""
            for provider in self._providers:
                if not provider.enabled:
                    continue
                
                try:
                    # Run async in thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    response_text = loop.run_until_complete(provider.get_strategy(prompt))
                    loop.close()
                    
                    if response_text:
                        break
                except Exception as e:
                    print(f"[Strategist] Provider error: {e}")
            
            # Parse response
            strategy = self._parse_response(request.request_id, response_text)
            self._response_queue.append(strategy)
    
    def _build_prompt(self, request: StrategyRequest) -> str:
        """Build LLM prompt from request data."""
        tendencies = request.player_tendencies
        
        prompt = f"""You are the tactical coordinator for enemy guards in a stealth maze game.

SITUATION:
- Floor: {request.floor_number}
- Enemies searching for player: {len(request.enemy_positions)}
- Enemy positions: {request.enemy_positions[:3]}  # First 3
- Last seen player at: {request.last_known_player_pos or "Unknown"}

PLAYER BEHAVIOR ANALYSIS:
- Hiding preference: {tendencies.get('hiding_preference', 0):.1%} (how often they hide)
- Stealth usage: {tendencies.get('stealth_ratio', 0):.1%} (how often they use stealth)
- Favorite hiding spots: {tendencies.get('favorite_hiding_spots', [])[:3]}
- Known danger zones: {tendencies.get('danger_zones', [])[:3]}
- Door escape rate: {tendencies.get('doors_for_escape_ratio', 0):.1%}

TASK: Suggest where enemies should search. Respond in JSON format:
{{"positions": [[x1,y1], [x2,y2]], "formation": "spread|group|ambush", "reason": "brief explanation"}}"""

        return prompt
    
    def _parse_response(self, request_id: str, response_text: str) -> StrategyResponse:
        """Parse LLM response into StrategyResponse."""
        # Default fallback
        default = StrategyResponse(
            request_id=request_id,
            suggested_positions=[],
            suggested_formation="spread",
            reasoning="Unable to get LLM response",
            confidence=0.0
        )
        
        if not response_text:
            return default
        
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                positions = data.get("positions", [])
                formation = data.get("formation", "spread")
                reason = data.get("reason", "LLM strategy")
                
                return StrategyResponse(
                    request_id=request_id,
                    suggested_positions=[tuple(p) for p in positions if len(p) == 2],
                    suggested_formation=formation,
                    reasoning=reason,
                    confidence=0.7
                )
        except (json.JSONDecodeError, Exception) as e:
            print(f"[Strategist] Parse error: {e}")
        
        return default
    
    def get_fallback_strategy(self, game, enemies: list) -> StrategyResponse:
        """
        Get a rule-based fallback strategy when LLM is unavailable.
        Uses player behavior data for smart defaults.
        """
        positions = []
        formation = "spread"
        reason = "Rule-based fallback"
        
        if hasattr(game, 'behavior_tracker') and game.behavior_tracker:
            tracker = game.behavior_tracker
            
            # Check favorite hiding spots
            hiding_spots = tracker.get_likely_hiding_spots(3)
            if hiding_spots:
                positions.extend(hiding_spots[:2])
                reason = "Checking player's favorite hiding spots"
            
            # Check hot zones
            hot_zones = tracker.get_hot_zones(3)
            if hot_zones:
                positions.extend(hot_zones[:2])
            
            # If player uses doors for escape, watch exits
            tendencies = tracker.get_player_tendencies()
            if tendencies.get('doors_for_escape_ratio', 0) > 0.5:
                formation = "ambush"
                reason = "Player often escapes through doors - setting ambush"
        
        return StrategyResponse(
            request_id="fallback",
            suggested_positions=positions[:4],
            suggested_formation=formation,
            reasoning=reason,
            confidence=0.5
        )
    
    def shutdown(self):
        """Clean up resources."""
        self._running = False
        if self._query_thread and self._query_thread.is_alive():
            self._query_thread.join(timeout=1.0)
