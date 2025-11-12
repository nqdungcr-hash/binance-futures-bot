"""
Binance Futures Grid Trading Bot - HEDGE MODE ONLY
VERSION: 2.2.1 COMPLETE - FIXED POSITION TAKE PROFIT & STOP LOSS
✅ All v2.2.0 features (GUI, multi-tab, scanner)
✅ AUTO CLOSE positions when TP/SL hit
✅ Per-position trailing stop
✅ Smart position management
✅ Optimized for small capital (10-100 USD)
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import json
import os
import math
from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException
import pandas as pd
import numpy as np
import requests
import atexit

class BinanceFuturesBot:
    def __init__(self, api_key, api_secret, use_testnet=True, bot_id=None):
        self.use_testnet = use_testnet
        self.bot_id = bot_id or "default"
        
        # Clean API credentials
        api_key = api_key.strip().replace(' ', '').replace('\n', '').replace('\r', '')
        api_secret = api_secret.strip().replace(' ', '').replace('\n', '').replace('\r', '')
        
        if use_testnet:
            self.client = Client(api_key, api_secret, testnet=True)
            self.client.API_URL = 'https://testnet.binancefuture.com'
            print(f"🧪 [{self.bot_id}] Using TESTNET")
        else:
            self.client = Client(api_key, api_secret)
            print(f"💰 [{self.bot_id}] Using REAL BINANCE")
        
        # Bot settings
        self.symbol = "BTCUSDT"
        self.leverage = 10
        self.grid_count = 10
        self.capital = 1000
        self.grid_range_percent = 2
        self.auto_grid = False
        self.stop_loss_percent = 5
        self.take_profit_percent = 10
        self.trailing_stop_percent = 2
        self.max_position_size_percent = 30
        self.initial_capital = 1000
        
        # 🆕 PER-POSITION TP/SL Settings (auto-optimized based on capital)
        self.enable_position_tp = True
        self.enable_position_sl = True
        self.position_tp_percent = 3.0
        self.position_sl_percent = 2.0
        self.position_trailing_percent = 1.5
        
        # Advanced features
        self.enable_dynamic_grid = True
        self.enable_trailing_per_position = True
        self.enable_auto_pause_resume = True
        self.volatility_threshold = 5
        self.trend_threshold = 3
        
        # Advanced risk management
        self.max_drawdown_percent = 15
        self.daily_loss_limit_percent = 10
        self.daily_start_balance = 0
        self.max_open_orders_per_side = 5
        
        # State
        self.is_running = False
        self.is_paused = False
        self.positions = []
        self.open_orders = []
        self.filled_orders = []
        self.pnl = 0
        self.balance = 0
        self.available_balance = 0
        
        # Market data
        self.current_price = 0
        self.market_state = "UNKNOWN"
        self.grid_levels = []
        
        # Grid stability
        self.grid_initialized = False
        self.grid_base_price = 0
        self.locked_grid_levels = []
        self.highest_balance = 0
        self.position_highest_pnl = {}
        
        # Order tracking
        self.last_filled_order_ids = set()
        self.active_order_ids = set()
        
        # Cooldown timers
        self.last_rebalance_time = 0
        self.rebalance_cooldown = 300
        self.last_pause_time = 0
        self.pause_cooldown = 180
        self.pause_timestamps = []
        self.max_pauses_per_hour = 3
        
        # Auto pause/resume tracking
        self.auto_paused = False
        self.pause_start_time = 0
        self.pause_count = 0
        self.stable_checks = 0
        self.required_stable_checks = 3
        
        # Symbol precision
        self.price_precision = 2
        self.quantity_precision = 3
        self.tick_size = 0.01
        self.step_size = 0.001
        self.min_qty = 0.001
        self.max_qty = 10000
        
        # Thread management
        self.bot_thread = None
        self.stop_event = threading.Event()
        
        # Small capital optimization
        self.min_capital = 10
        self.max_capital = 100
        self.is_small_capital = False
        
        print(f"✅ [{self.bot_id}] Bot initialized (v2.2.1)")
    
    def optimize_for_small_capital(self):
        """Auto-optimize settings for small capital (10-100 USD)"""
        self.is_small_capital = self.capital <= self.max_capital
        
        if self.is_small_capital:
            print(f"\n{'='*60}")
            print(f"💡 [{self.bot_id}] SMALL CAPITAL MODE ACTIVATED!")
            print(f"   Capital: ${self.capital:.2f}")
            print(f"{'='*60}")
            
            if self.capital < 20:
                self.grid_count = 4
                self.grid_range_percent = 1.0
                self.leverage = 5
                self.max_open_orders_per_side = 2
                self.position_tp_percent = 2.0
                self.position_sl_percent = 1.0
                self.position_trailing_percent = 0.8
                
            elif self.capital < 50:
                self.grid_count = 6
                self.grid_range_percent = 1.5
                self.leverage = 7
                self.max_open_orders_per_side = 3
                self.position_tp_percent = 2.5
                self.position_sl_percent = 1.5
                self.position_trailing_percent = 1.0
                
            elif self.capital <= 100:
                self.grid_count = 8
                self.grid_range_percent = 2.0
                self.leverage = 10
                self.max_open_orders_per_side = 4
                self.position_tp_percent = 3.0
                self.position_sl_percent = 2.0
                self.position_trailing_percent = 1.5
            
            self.stop_loss_percent = 3
            self.take_profit_percent = 5
            self.trailing_stop_percent = 1.5
            self.max_drawdown_percent = 10
            self.daily_loss_limit_percent = 5
            self.volatility_threshold = 3
            self.trend_threshold = 2
            
            print(f"   📊 Auto-adjusted settings:")
            print(f"      Grid Count: {self.grid_count}")
            print(f"      Grid Range: {self.grid_range_percent}%")
            print(f"      Leverage: {self.leverage}x")
            print(f"      Max Orders/Side: {self.max_open_orders_per_side}")
            print(f"   🎯 PER-POSITION TP/SL:")
            print(f"      Position Take Profit: {self.position_tp_percent}% ✅")
            print(f"      Position Stop Loss: {self.position_sl_percent}% ❌")
            print(f"      Position Trailing: {self.position_trailing_percent}% 📉")
            print(f"   ⚖️ RISK:REWARD = 1:{self.position_tp_percent/self.position_sl_percent:.2f}")
            
            required_wr = self.position_sl_percent / (self.position_sl_percent + self.position_tp_percent) * 100
            print(f"   📈 Required Win Rate: >{required_wr:.1f}% to break even")
            print(f"{'='*60}\n")
        
        else:
            print(f"\n{'='*60}")
            print(f"💰 [{self.bot_id}] STANDARD MODE")
            print(f"   Capital: ${self.capital:.2f}")
            print(f"{'='*60}")
            
            if self.capital < 500:
                self.position_tp_percent = 3.5
                self.position_sl_percent = 2.5
                self.position_trailing_percent = 1.8
            elif self.capital < 1000:
                self.position_tp_percent = 4.0
                self.position_sl_percent = 2.5
                self.position_trailing_percent = 2.0
            else:
                self.position_tp_percent = 5.0
                self.position_sl_percent = 3.0
                self.position_trailing_percent = 2.5
            
            print(f"   🎯 PER-POSITION TP/SL:")
            print(f"      Take Profit: {self.position_tp_percent}% ✅")
            print(f"      Stop Loss: {self.position_sl_percent}% ❌")
            print(f"      Trailing: {self.position_trailing_percent}% 📉")
            print(f"   ⚖️ RISK:REWARD = 1:{self.position_tp_percent/self.position_sl_percent:.2f}")
            print(f"{'='*60}\n")
    
    def calculate_optimal_grid_spacing(self):
        """Calculate optimal grid spacing based on capital and volatility"""
        try:
            klines = self.client.futures_klines(symbol=self.symbol, interval='15m', limit=96)
            df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 
                                               'close_time', 'quote_volume', 'trades', 
                                               'taker_buy_base', 'taker_buy_quote', 'ignore'])
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            
            df['tr'] = df[['high', 'low', 'close']].apply(
                lambda x: max(x['high'] - x['low'], 
                             abs(x['high'] - x['close']), 
                             abs(x['low'] - x['close'])), axis=1)
            atr = df['tr'].tail(24).mean()
            atr_percent = (atr / self.current_price) * 100
            
            if self.is_small_capital:
                base_range = min(atr_percent * 0.8, 2.0)
            else:
                base_range = min(atr_percent * 1.2, 3.0)
            
            self.grid_range_percent = round(base_range, 2)
            
            print(f"🔍 [{self.bot_id}] Optimal Grid Spacing:")
            print(f"   ATR: ${atr:.2f} ({atr_percent:.2f}%)")
            print(f"   Adjusted Range: {self.grid_range_percent}%")
            
        except Exception as e:
            print(f"⚠️ [{self.bot_id}] Could not calculate optimal spacing: {e}")
    
    def test_connection(self):
        """Test API connection"""
        try:
            server_time = self.client.get_server_time()
            print(f"✅ [{self.bot_id}] Server connected! Time: {datetime.fromtimestamp(server_time['serverTime']/1000)}")
            
            account = self.client.futures_account()
            print(f"✅ [{self.bot_id}] Account access OK! Assets: {len(account['assets'])}")
            
            if not account:
                return False, "❌ Futures account not accessible"
            
            return True, "✅ Connection successful!"
            
        except BinanceAPIException as e:
            if e.code == -2014:
                return False, f"❌ API Key Format Invalid! ({e.code}): {e.message}"
            elif e.code == -2015:
                return False, f"❌ Invalid API Key! ({e.code}): {e.message}"
            else:
                return False, f"❌ API Error ({e.code}): {e.message}"
        except Exception as e:
            return False, f"❌ Connection Error: {str(e)}"
    
    def get_symbol_info(self):
        """Get symbol precision"""
        try:
            info = self.client.futures_exchange_info()
            for s in info['symbols']:
                if s['symbol'] == self.symbol:
                    self.price_precision = s['pricePrecision']
                    self.quantity_precision = s['quantityPrecision']
                    
                    for f in s['filters']:
                        if f['filterType'] == 'PRICE_FILTER':
                            self.tick_size = float(f['tickSize'])
                        elif f['filterType'] == 'LOT_SIZE':
                            self.step_size = float(f['stepSize'])
                            self.min_qty = float(f['minQty'])
                            self.max_qty = float(f['maxQty'])
                    
                    print(f"✅ [{self.bot_id}] {self.symbol} Info:")
                    print(f"   Price precision: {self.price_precision}, Tick: {self.tick_size}")
                    print(f"   Qty precision: {self.quantity_precision}, Step: {self.step_size}")
                    break
        except Exception as e:
            print(f"[{self.bot_id}] Error getting symbol info: {str(e)}")
    
    def round_price(self, price):
        """Round price to tick size"""
        from decimal import Decimal, ROUND_DOWN
        tick = Decimal(str(self.tick_size))
        price_decimal = Decimal(str(price))
        rounded = (price_decimal / tick).quantize(Decimal('1'), rounding=ROUND_DOWN) * tick
        return float(rounded)
    
    def round_quantity(self, quantity):
        """Round quantity to step size"""
        if quantity <= 0:
            return 0
        from decimal import Decimal, ROUND_DOWN
        step = Decimal(str(self.step_size))
        qty_decimal = Decimal(str(quantity))
        rounded = (qty_decimal / step).quantize(Decimal('1'), rounding=ROUND_DOWN) * step
        return float(rounded)
    
    def initialize(self):
        try:
            print(f"\n{'='*60}")
            print(f"🔍 [{self.bot_id}] Testing API connection...")
            print(f"{'='*60}")
            
            success, msg = self.test_connection()
            if not success:
                return False, msg
            
            print(f"✅ [{self.bot_id}] Connection test passed!")
            
            self.get_symbol_info()
            
            try:
                self.client.futures_cancel_all_open_orders(symbol=self.symbol)
                print(f"✅ [{self.bot_id}] Cancelled all old orders for {self.symbol}")
            except:
                pass
            
            self.client.futures_change_leverage(symbol=self.symbol, leverage=self.leverage)
            print(f"✅ [{self.bot_id}] Leverage: {self.leverage}x")
            
            try:
                current_mode = self.client.futures_get_position_mode()
                if not current_mode['dualSidePosition']:
                    self.client.futures_change_position_mode(dualSidePosition=True)
                    print(f"✅ [{self.bot_id}] ENABLED Hedge Mode")
                else:
                    print(f"✅ [{self.bot_id}] Hedge Mode already enabled")
            except BinanceAPIException as e:
                if e.code == -4059:
                    print(f"✅ [{self.bot_id}] Hedge Mode already enabled")
                elif e.code == -4067:
                    print(f"⚠️ [{self.bot_id}] Cannot change position mode - open orders exist")
                    return False, "Error: Open orders exist, cannot change position mode"
                else:
                    print(f"⚠️ [{self.bot_id}] Hedge Mode error: {str(e)}")
            
            self.update_balance()
            self.initial_capital = self.balance
            self.highest_balance = self.balance
            self.daily_start_balance = self.balance
            
            ticker = self.client.futures_symbol_ticker(symbol=self.symbol)
            self.current_price = float(ticker['price'])
            
            self.optimize_for_small_capital()
            self.calculate_optimal_grid_spacing()
            self.calculate_and_lock_grid_levels()
            
            self.last_rebalance_time = time.time()
            self.last_pause_time = 0
            self.pause_timestamps = []
            
            mode = "TESTNET" if self.use_testnet else "REAL"
            return True, f"✅ [{self.bot_id}] Initialization successful! ({mode})"
        except BinanceAPIException as e:
            return False, f"API Error ({e.code}): {e.message}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def calculate_and_lock_grid_levels(self):
        """Calculate grid levels and LOCK them"""
        if self.auto_grid:
            if self.capital < 20:
                self.grid_count = 4
            elif self.capital < 50:
                self.grid_count = 6
            elif self.capital < 100:
                self.grid_count = 8
            elif self.capital < 500:
                self.grid_count = 10
            elif self.capital < 2000:
                self.grid_count = 15
            else:
                self.grid_count = 20
        
        self.grid_base_price = self.current_price
        
        upper_price = self.grid_base_price * (1 + self.grid_range_percent / 100)
        lower_price = self.grid_base_price * (1 - self.grid_range_percent / 100)
        
        step = (upper_price - lower_price) / (self.grid_count - 1)
        
        self.locked_grid_levels = [lower_price + i * step for i in range(self.grid_count)]
        self.grid_levels = self.locked_grid_levels.copy()
        
        print(f"🔒 [{self.bot_id}] LOCKED Grid Range: ${lower_price:.2f} - ${upper_price:.2f}")
        print(f"📊 [{self.bot_id}] Base Price: ${self.grid_base_price:.2f}")
        print(f"📊 [{self.bot_id}] Grid Count: {self.grid_count}")
        print(f"💡 [{self.bot_id}] Grid prices are now LOCKED (stable)")
    
    def check_grid_rebalance(self):
        """Check if need to rebalance grid"""
        if not self.grid_levels or not self.grid_initialized:
            return False
        
        upper_bound = max(self.locked_grid_levels)
        lower_bound = min(self.locked_grid_levels)
        
        grid_range = upper_bound - lower_bound
        buffer = grid_range * 0.20
        
        upper_trigger = upper_bound + buffer
        lower_trigger = lower_bound - buffer
        
        if self.current_price > upper_trigger:
            print(f"\n{'='*60}")
            print(f"⚠️ [{self.bot_id}] Price ${self.current_price:.2f} TOO HIGH!")
            print(f"   Grid: ${lower_bound:.2f} - ${upper_bound:.2f}")
            print(f"   Trigger: ${upper_trigger:.2f}")
            print(f"🔄 [{self.bot_id}] Rebalancing grid...")
            print(f"{'='*60}\n")
            
            self.calculate_and_lock_grid_levels()
            
            try:
                self.client.futures_cancel_all_open_orders(symbol=self.symbol)
                print(f"✅ [{self.bot_id}] Cancelled old orders")
            except Exception as e:
                print(f"⚠️ Cancel error: {e}")
            
            time.sleep(2)
            self.grid_initialized = False
            return True
            
        elif self.current_price < lower_trigger:
            print(f"\n{'='*60}")
            print(f"⚠️ [{self.bot_id}] Price ${self.current_price:.2f} TOO LOW!")
            print(f"   Grid: ${lower_bound:.2f} - ${upper_bound:.2f}")
            print(f"   Trigger: ${lower_trigger:.2f}")
            print(f"🔄 [{self.bot_id}] Rebalancing grid...")
            print(f"{'='*60}\n")
            
            self.calculate_and_lock_grid_levels()
            
            try:
                self.client.futures_cancel_all_open_orders(symbol=self.symbol)
                print(f"✅ [{self.bot_id}] Cancelled old orders")
            except Exception as e:
                print(f"⚠️ Cancel error: {e}")
            
            time.sleep(2)
            self.grid_initialized = False
            return True
        
        return False
    
    def update_balance(self):
        try:
            account = self.client.futures_account()
            for asset in account['assets']:
                if asset['asset'] == 'USDT':
                    self.balance = float(asset['walletBalance'])
                    self.available_balance = float(asset['availableBalance'])
                    
                    if self.balance > self.highest_balance:
                        self.highest_balance = self.balance
        except Exception as e:
            print(f"[{self.bot_id}] Error updating balance: {e}")
    
    def get_positions(self):
        try:
            positions = self.client.futures_position_information(symbol=self.symbol)
            self.positions = []
            for pos in positions:
                if float(pos['positionAmt']) != 0:
                    try:
                        leverage = int(pos.get('leverage', self.leverage))
                    except (ValueError, TypeError):
                        leverage = self.leverage
                    
                    position_key = f"{pos['symbol']}_{pos.get('positionSide', 'BOTH')}"
                    
                    self.positions.append({
                        'symbol': pos['symbol'],
                        'side': 'LONG' if float(pos['positionAmt']) > 0 else 'SHORT',
                        'amount': abs(float(pos['positionAmt'])),
                        'entry_price': float(pos['entryPrice']),
                        'unrealized_pnl': float(pos['unRealizedProfit']),
                        'leverage': leverage,
                        'position_side': pos.get('positionSide', 'BOTH'),
                        'position_key': position_key,
                        'mark_price': float(pos.get('markPrice', 0)),
                        'liquidation_price': float(pos.get('liquidationPrice', 0))
                    })
                    
                    if position_key not in self.position_highest_pnl:
                        self.position_highest_pnl[position_key] = float(pos['unRealizedProfit'])
                    else:
                        current_pnl = float(pos['unRealizedProfit'])
                        if current_pnl > self.position_highest_pnl[position_key]:
                            self.position_highest_pnl[position_key] = current_pnl
            
            return self.positions
        except Exception as e:
            print(f"[{self.bot_id}] Error getting positions: {str(e)}")
            return []
    
    def get_open_orders(self):
        try:
            orders = self.client.futures_get_open_orders(symbol=self.symbol)
            self.open_orders = []
            for order in orders:
                self.open_orders.append({
                    'order_id': order['orderId'],
                    'symbol': order['symbol'],
                    'side': order['side'],
                    'type': order['type'],
                    'price': float(order['price']),
                    'quantity': float(order['origQty']),
                    'filled': float(order['executedQty']),
                    'status': order['status'],
                    'time': datetime.fromtimestamp(order['time']/1000).strftime('%H:%M:%S'),
                    'position_side': order.get('positionSide', 'BOTH')
                })
            return self.open_orders
        except Exception as e:
            print(f"[{self.bot_id}] Error getting open orders: {str(e)}")
            return []
    
    def get_filled_orders(self, limit=50):
        try:
            trades = self.client.futures_account_trades(symbol=self.symbol, limit=limit)
            self.filled_orders = []
            for trade in trades:
                self.filled_orders.append({
                    'id': trade['id'],
                    'symbol': trade['symbol'],
                    'side': trade['side'],
                    'price': float(trade['price']),
                    'quantity': float(trade['qty']),
                    'commission': float(trade['commission']),
                    'realized_pnl': float(trade['realizedPnl']),
                    'time': datetime.fromtimestamp(trade['time']/1000).strftime('%H:%M:%S'),
                    'position_side': trade.get('positionSide', 'BOTH')
                })
            return self.filled_orders
        except Exception as e:
            print(f"[{self.bot_id}] Error getting filled orders: {str(e)}")
            return []
    
    def check_position_tp_sl(self):
        """🆕 Check and close positions based on TP/SL"""
        if not self.enable_position_tp and not self.enable_position_sl:
            return
        
        try:
            self.get_positions()
            
            for pos in self.positions:
                position_key = pos['position_key']
                entry_price = pos['entry_price']
                current_pnl = pos['unrealized_pnl']
                amount = pos['amount']
                position_side = pos['position_side']
                
                position_value = entry_price * amount
                pnl_percent = (current_pnl / position_value) * 100 if position_value > 0 else 0
                
                should_close = False
                close_reason = ""
                
                if self.enable_position_tp and pnl_percent >= self.position_tp_percent:
                    should_close = True
                    close_reason = f"✅ TAKE PROFIT ({pnl_percent:.4f}% >= {self.position_tp_percent}%)"
                
                elif self.enable_position_sl and pnl_percent <= -self.position_sl_percent:
                    should_close = True
                    close_reason = f"🛑 STOP LOSS ({pnl_percent:.4f}% <= -{self.position_sl_percent}%)"
                
                elif self.enable_trailing_per_position and current_pnl > 0:
                    highest_pnl = self.position_highest_pnl.get(position_key, 0)
                    if highest_pnl > 0:
                        pnl_drop = ((highest_pnl - current_pnl) / highest_pnl) * 100
                        if pnl_drop >= self.position_trailing_percent:
                            should_close = True
                            close_reason = f"📉 TRAILING STOP ({pnl_drop:.4f}% drop from peak ${highest_pnl:.8f})"
                
                if not should_close and abs(pnl_percent) > 0.5:
                    status_color = "🟢" if current_pnl > 0 else "🔴"
                    highest_pnl = self.position_highest_pnl.get(position_key, 0)
                    print(f"{status_color} [{self.bot_id}] {position_side} | "
                          f"PnL: {pnl_percent:+.4f}% (${current_pnl:.8f}) | "
                          f"Peak: ${highest_pnl:.8f} | "
                          f"TP:{self.position_tp_percent}% SL:-{self.position_sl_percent}% Trail:{self.position_trailing_percent}%")
                
                if should_close:
                    self.close_position(pos, close_reason)
                    
        except Exception as e:
            print(f"[{self.bot_id}] Error checking position TP/SL: {str(e)}")
    
    def close_position(self, position, reason):
        """🆕 Close a specific position - NO ROUNDING (use exact amount from Binance)"""
        try:
            print(f"\n{'='*60}")
            print(f"🎯 [{self.bot_id}] CLOSING POSITION")
            print(f"   Reason: {reason}")
            print(f"   Symbol: {position['symbol']}")
            print(f"   Side: {position['side']} ({position['position_side']})")
            print(f"   Amount: {position['amount']} (EXACT from Binance)")
            print(f"   Entry: ${position['entry_price']}")
            print(f"   Current: ${self.current_price}")
            print(f"   PnL: ${position['unrealized_pnl']:.8f}")
            print(f"{'='*60}\n")
            
            close_side = 'SELL' if position['side'] == 'LONG' else 'BUY'
            
            # 🔥 NO ROUNDING - Use exact amount from Binance API
            order = self.client.futures_create_order(
                symbol=position['symbol'],
                side=close_side,
                positionSide=position['position_side'],
                type='MARKET',
                quantity=position['amount']
            )
            
            print(f"✅ [{self.bot_id}] Position closed successfully!")
            print(f"   Order ID: {order['orderId']}")
            print(f"   Realized PnL: ${position['unrealized_pnl']:.8f}")
            
            if position['position_key'] in self.position_highest_pnl:
                del self.position_highest_pnl[position['position_key']]
            
        except Exception as e:
            print(f"❌ [{self.bot_id}] Error closing position: {str(e)}")
    
    def check_risk_management(self):
        """Risk management checks - BOT LEVEL"""
        self.update_balance()
        
        if self.stop_loss_percent > 0:
            loss_amount = self.initial_capital - self.balance
            loss_percent = (loss_amount / self.initial_capital) * 100
            
            if loss_percent >= self.stop_loss_percent:
                return True, f"🛑 [{self.bot_id}] Stop Loss triggered! Loss: {loss_percent:.2f}%"
        
        drawdown = ((self.highest_balance - self.balance) / self.highest_balance) * 100
        if drawdown >= self.max_drawdown_percent:
            return True, f"🛑 [{self.bot_id}] Max Drawdown reached! Drawdown: {drawdown:.2f}%"
        
        daily_loss = self.daily_start_balance - self.balance
        daily_loss_percent = (daily_loss / self.daily_start_balance) * 100
        if daily_loss_percent >= self.daily_loss_limit_percent:
            return True, f"🛑 [{self.bot_id}] Daily Loss Limit! Loss today: {daily_loss_percent:.2f}%"
        
        if self.take_profit_percent > 0:
            profit = self.balance - self.initial_capital
            profit_percent = (profit / self.initial_capital) * 100
            
            if profit_percent >= self.take_profit_percent:
                return True, f"🎯 [{self.bot_id}] Take Profit reached! Profit: {profit_percent:.2f}%"
        
        if self.trailing_stop_percent > 0 and self.highest_balance > self.initial_capital:
            trailing_loss = ((self.highest_balance - self.balance) / self.highest_balance) * 100
            if trailing_loss >= self.trailing_stop_percent:
                return True, f"📉 [{self.bot_id}] Trailing Stop triggered! Drop: {trailing_loss:.2f}%"
        
        return False, ""
    
    def analyze_market(self):
        """Market analysis with cooldown protection"""
        try:
            klines = self.client.futures_klines(symbol=self.symbol, interval='1h', limit=24)
            df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 
                                               'close_time', 'quote_volume', 'trades', 
                                               'taker_buy_base', 'taker_buy_quote', 'ignore'])
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            
            volatility = (df['high'].max() - df['low'].min()) / df['close'].mean() * 100
            
            sma_short = df['close'].tail(6).mean()
            sma_long = df['close'].tail(24).mean()
            trend_strength = ((sma_short - sma_long) / sma_long) * 100
            
            try:
                funding_info = self.client.futures_funding_rate(symbol=self.symbol, limit=1)
                funding_rate = float(funding_info[0]['fundingRate']) * 100
            except:
                funding_rate = 0
            
            is_stable = (abs(trend_strength) <= self.trend_threshold and 
                        volatility <= self.volatility_threshold and 
                        abs(funding_rate) <= 0.1)
            
            current_time = time.time()
            
            self.pause_timestamps = [t for t in self.pause_timestamps 
                                      if current_time - t < 3600]
            
            if self.enable_auto_pause_resume:
                if is_stable:
                    self.stable_checks += 1
                    
                    if self.auto_paused and self.stable_checks >= self.required_stable_checks:
                        if current_time - self.last_pause_time < self.pause_cooldown:
                            remaining = self.pause_cooldown - (current_time - self.last_pause_time)
                            return False, f"⏳ [{self.bot_id}] Resume cooldown: {remaining:.0f}s"
                        
                        pause_duration = time.time() - self.pause_start_time
                        print(f"\n{'='*60}")
                        print(f"✅ [{self.bot_id}] MARKET STABLE AGAIN!")
                        print(f"📊 Volatility: {volatility:.2f}% (OK)")
                        print(f"📈 Trend: {trend_strength:.2f}% (OK)")
                        print(f"⏱️ Paused for: {pause_duration/60:.1f} minutes")
                        print(f"🔄 [{self.bot_id}] AUTO RESUME...")
                        print(f"{'='*60}\n")
                        
                        self.auto_paused = False
                        self.is_paused = False
                        self.stable_checks = 0
                        self.pause_count += 1
                        
                        self.update_price()
                        
                        try:
                            self.client.futures_cancel_all_open_orders(symbol=self.symbol)
                            print(f"✅ [{self.bot_id}] Cancelled old orders")
                        except:
                            pass
                        
                        time.sleep(2)
                        self.calculate_and_lock_grid_levels()
                        self.grid_initialized = False
                        
                        return True, f"🔄 [{self.bot_id}] RESUMED! Stable market"
                else:
                    self.stable_checks = 0
                    
                    if not self.auto_paused and self.grid_initialized:
                        if len(self.pause_timestamps) >= self.max_pauses_per_hour:
                            print(f"⚠️ [{self.bot_id}] Too many pauses ({len(self.pause_timestamps)}/hour)!")
                            self.enable_auto_pause_resume = False
                            return True, f"⚠️ Auto pause disabled (too frequent)"
                        
                        if current_time - self.last_pause_time < self.pause_cooldown:
                            remaining = self.pause_cooldown - (current_time - self.last_pause_time)
                            return True, f"⏳ [{self.bot_id}] Pause cooldown: {remaining:.0f}s"
                        
                        if abs(trend_strength) > self.trend_threshold:
                            print(f"\n{'='*60}")
                            print(f"⚠️ [{self.bot_id}] STRONG TREND DETECTED!")
                            print(f"📈 Trend: {trend_strength:.2f}%")
                            print(f"🛑 [{self.bot_id}] AUTO PAUSE")
                            print(f"{'='*60}\n")
                            
                            self.auto_paused = True
                            self.is_paused = True
                            self.pause_start_time = time.time()
                            self.last_pause_time = current_time
                            self.pause_timestamps.append(current_time)
                            
                            try:
                                self.client.futures_cancel_all_open_orders(symbol=self.symbol)
                            except:
                                pass
                        
                        elif volatility > self.volatility_threshold:
                            print(f"\n{'='*60}")
                            print(f"⚠️ [{self.bot_id}] HIGH VOLATILITY!")
                            print(f"📊 Volatility: {volatility:.2f}%")
                            print(f"🛑 [{self.bot_id}] AUTO PAUSE")
                            print(f"{'='*60}\n")
                            
                            self.auto_paused = True
                            self.is_paused = True
                            self.pause_start_time = time.time()
                            self.last_pause_time = current_time
                            self.pause_timestamps.append(current_time)
            
            if self.auto_paused:
                pause_duration = (time.time() - self.pause_start_time) / 60
                return False, f"⏸️ [{self.bot_id}] AUTO PAUSED ({pause_duration:.1f}m) - Waiting..."
            
            if abs(trend_strength) > self.trend_threshold:
                self.market_state = "UPTREND" if trend_strength > 0 else "DOWNTREND"
                return False, f"📈 [{self.bot_id}] Strong trend ({trend_strength:.2f}%)"
            
            elif volatility > self.volatility_threshold:
                self.market_state = "HIGH_VOLATILITY"
                return False, f"📊 [{self.bot_id}] High volatility ({volatility:.2f}%)"
            
            else:
                self.market_state = "SIDEWAY"
                return True, f"🔄 [{self.bot_id}] Stable sideway"
                
        except Exception as e:
            print(f"[{self.bot_id}] Error in market analysis: {str(e)}")
            return False, f"Analysis error: {str(e)}"
    
    def update_price(self):
        try:
            ticker = self.client.futures_symbol_ticker(symbol=self.symbol)
            self.current_price = float(ticker['price'])
        except:
            pass
    
    def place_hedge_grid_orders(self):
        """Place STABLE grid orders using LOCKED prices"""
        try:
            max_position_value = self.capital * (self.max_position_size_percent / 100)
            total_grids = len(self.locked_grid_levels)
            
            capital_per_side = self.capital / 2
            qty_per_grid = (capital_per_side / (total_grids / 2)) / self.current_price
            qty_per_grid = self.round_quantity(qty_per_grid)
            
            if qty_per_grid <= 0 or qty_per_grid < self.min_qty:
                print(f"⚠️ [{self.bot_id}] Quantity too small: {qty_per_grid}")
                return
            
            print(f"🎯 [{self.bot_id}] Placing {total_grids} STABLE grid orders:")
            print(f"   💰 Capital per side: ${capital_per_side:.2f}")
            print(f"   📊 Per order: {qty_per_grid} {self.symbol}")
            print(f"   🔒 Using LOCKED grid prices (stable!)")
            
            long_count = 0
            short_count = 0
            
            for level in self.locked_grid_levels:
                rounded_price = self.round_price(level)
                price_str = f"{rounded_price:.{self.price_precision}f}"
                qty_str = f"{qty_per_grid:.{self.quantity_precision}f}"
                
                try:
                    if level < self.grid_base_price and long_count < self.max_open_orders_per_side:
                        self.client.futures_create_order(
                            symbol=self.symbol,
                            side='BUY',
                            positionSide='LONG',
                            type='LIMIT',
                            timeInForce='GTC',
                            quantity=qty_str,
                            price=price_str
                        )
                        long_count += 1
                        print(f"  ✅ BUY LONG @ {price_str} (LOCKED)")
                        time.sleep(0.15)
                    
                    elif level > self.grid_base_price and short_count < self.max_open_orders_per_side:
                        self.client.futures_create_order(
                            symbol=self.symbol,
                            side='SELL',
                            positionSide='SHORT',
                            type='LIMIT',
                            timeInForce='GTC',
                            quantity=qty_str,
                            price=price_str
                        )
                        short_count += 1
                        print(f"  ✅ SELL SHORT @ {price_str} (LOCKED)")
                        time.sleep(0.15)
                        
                except BinanceAPIException as e:
                    if e.code == -2021:
                        print(f"  ⚠️ Skip {price_str}: would match immediately")
                    else:
                        print(f"  ⚠️ Error at {price_str}: {e.message}")
                except Exception as e:
                    print(f"  ⚠️ Error at {price_str}: {str(e)}")
            
            total_placed = long_count + short_count
            if total_placed > 0:
                print(f"✅ [{self.bot_id}] Placed {total_placed} STABLE orders ({long_count} LONG + {short_count} SHORT)!")
                self.grid_initialized = True
            else:
                print(f"❌ [{self.bot_id}] No orders placed!")
            
        except Exception as e:
            print(f"[{self.bot_id}] Error placing orders: {str(e)}")
    
    def refill_hedge_orders(self):
        """Refill orders using order ID tracking"""
        try:
            self.get_filled_orders(limit=100)
            current_filled_ids = {order['id'] for order in self.filled_orders}
            
            new_fills = current_filled_ids - self.last_filled_order_ids
            
            if not new_fills:
                return
            
            print(f"🔄 [{self.bot_id}] {len(new_fills)} new fills detected! Refilling...")
            
            self.last_filled_order_ids = current_filled_ids
            
            self.get_open_orders()
            self.active_order_ids = {order['order_id'] for order in self.open_orders}
            
            open_prices_long = {self.round_price(o['price']) 
                                for o in self.open_orders 
                                if o['position_side'] == 'LONG'}
            open_prices_short = {self.round_price(o['price']) 
                                 for o in self.open_orders 
                                 if o['position_side'] == 'SHORT'}
            
            capital_per_side = self.capital / 2
            total_grids = len(self.locked_grid_levels)
            qty_per_grid = (capital_per_side / (total_grids / 2)) / self.current_price
            qty_per_grid = self.round_quantity(qty_per_grid)
            
            if qty_per_grid < self.min_qty:
                return
            
            long_count = len([o for o in self.open_orders if o['position_side'] == 'LONG'])
            short_count = len([o for o in self.open_orders if o['position_side'] == 'SHORT'])
            
            refilled = 0
            
            for level in self.locked_grid_levels:
                rounded_price = self.round_price(level)
                price_str = f"{rounded_price:.{self.price_precision}f}"
                qty_str = f"{qty_per_grid:.{self.quantity_precision}f}"
                
                try:
                    if (level < self.grid_base_price and 
                        rounded_price not in open_prices_long and 
                        long_count < self.max_open_orders_per_side):
                        
                        self.client.futures_create_order(
                            symbol=self.symbol,
                            side='BUY',
                            positionSide='LONG',
                            type='LIMIT',
                            timeInForce='GTC',
                            quantity=qty_str,
                            price=price_str
                        )
                        refilled += 1
                        long_count += 1
                        open_prices_long.add(rounded_price)
                        print(f"  🔄 Refilled BUY LONG @ {price_str}")
                        time.sleep(0.15)
                    
                    elif (level > self.grid_base_price and 
                          rounded_price not in open_prices_short and 
                          short_count < self.max_open_orders_per_side):
                        
                        self.client.futures_create_order(
                            symbol=self.symbol,
                            side='SELL',
                            positionSide='SHORT',
                            type='LIMIT',
                            timeInForce='GTC',
                            quantity=qty_str,
                            price=price_str
                        )
                        refilled += 1
                        short_count += 1
                        open_prices_short.add(rounded_price)
                        print(f"  🔄 Refilled SELL SHORT @ {price_str}")
                        time.sleep(0.15)
                        
                except BinanceAPIException as e:
                    if e.code == -2021:
                        print(f"  ⚠️ Skip {price_str}: would match immediately")
                    else:
                        print(f"  ⚠️ Cannot refill @ {price_str}: {e.message}")
                except Exception as e:
                    print(f"  ⚠️ Error @ {price_str}: {str(e)}")
            
            if refilled > 0:
                print(f"✅ [{self.bot_id}] Refilled {refilled} orders!")
                
        except Exception as e:
            print(f"[{self.bot_id}] Refill error: {str(e)}")
    
    def calculate_pnl(self):
        try:
            account = self.client.futures_account()
            self.pnl = float(account['totalUnrealizedProfit'])
            self.update_balance()
        except:
            pass
    
    def run_bot(self):
        """Bot loop with TP/SL checks"""
        print(f"▶️ [{self.bot_id}] Bot thread started")
        
        while self.is_running and not self.stop_event.is_set():
            try:
                self.update_price()
                
                # 🆕 Check position TP/SL FIRST
                self.check_position_tp_sl()
                
                stop_triggered, stop_msg = self.check_risk_management()
                if stop_triggered:
                    print(stop_msg)
                    self.stop()
                    break
                
                should_run, message = self.analyze_market()
                
                current_time = time.time()
                if (self.enable_dynamic_grid and 
                    self.grid_initialized and 
                    not self.auto_paused):
                    
                    if current_time - self.last_rebalance_time >= self.rebalance_cooldown:
                        if self.check_grid_rebalance():
                            print(f"🔄 [{self.bot_id}] Grid rebalanced!")
                            self.last_rebalance_time = current_time
                            time.sleep(3)
                
                if not self.is_paused:
                    if not self.grid_initialized and should_run:
                        print(f"🎯 [{self.bot_id}] {message}")
                        self.place_hedge_grid_orders()
                        self.last_rebalance_time = current_time
                    
                    elif self.grid_initialized and should_run:
                        self.refill_hedge_orders()
                    
                    elif self.grid_initialized and not should_run and not self.auto_paused:
                        print(f"⚠️ [{self.bot_id}] {message}")
                
                self.calculate_pnl()
                self.get_positions()
                self.get_open_orders()
                self.get_filled_orders()
                
                time.sleep(30)
                
            except Exception as e:
                print(f"[{self.bot_id}] Error in loop: {str(e)}")
                time.sleep(10)
        
        print(f"⏹️ [{self.bot_id}] Bot thread stopped")
    
    def start(self):
        """Start bot with independent thread"""
        if not self.is_running:
            self.is_running = True
            self.is_paused = False
            self.stop_event.clear()
            
            self.bot_thread = threading.Thread(
                target=self.run_bot, 
                daemon=True,
                name=f"Bot-{self.bot_id}"
            )
            self.bot_thread.start()
            print(f"✅ [{self.bot_id}] Started on independent thread: {self.bot_thread.name}")
    
    def stop(self):
        """Stop bot and clean up - NO ROUNDING (use exact amounts)"""
        print(f"\n{'='*60}")
        print(f"🛑 [{self.bot_id}] Stopping bot...")
        print(f"{'='*60}")
        
        self.is_running = False
        self.grid_initialized = False
        self.auto_paused = False
        self.stop_event.set()
        
        try:
            self.client.futures_cancel_all_open_orders(symbol=self.symbol)
            print(f"✅ [{self.bot_id}] Cancelled all orders for {self.symbol}")
            
            positions = self.client.futures_position_information(symbol=self.symbol)
            for pos in positions:
                position_amt = float(pos['positionAmt'])
                if position_amt != 0:
                    close_side = 'SELL' if position_amt > 0 else 'BUY'
                    pos_side = pos.get('positionSide', 'BOTH')
                    
                    # 🔥 NO ROUNDING - Use exact amount from Binance API
                    abs_amt = abs(position_amt)
                    
                    try:
                        self.client.futures_create_order(
                            symbol=self.symbol,
                            side=close_side,
                            positionSide=pos_side,
                            type='MARKET',
                            quantity=abs_amt
                        )
                        print(f"✅ [{self.bot_id}] Closed position {pos_side}: {abs_amt} (EXACT from Binance)")
                    except BinanceAPIException as e:
                        print(f"⚠️ [{self.bot_id}] Error closing {pos_side}: {e.message}")
                    except Exception as e:
                        print(f"⚠️ [{self.bot_id}] Error closing {pos_side}: {str(e)}")
            
            self.positions = []
            self.open_orders = []
            self.filled_orders = []
            self.locked_grid_levels = []
            self.grid_levels = []
            self.last_filled_order_ids = set()
            self.active_order_ids = set()
            print(f"🗑️ [{self.bot_id}] Cleaned cache")
            
            if self.pause_count > 0:
                print(f"\n📊 [{self.bot_id}] AUTO PAUSE STATISTICS:")
                print(f"   Auto pause count: {self.pause_count}")
            
            print(f"✅ [{self.bot_id}] Bot stopped successfully")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"[{self.bot_id}] Error during stop: {str(e)}")
    
    def pause(self):
        if not self.auto_paused:
            self.is_paused = True
            print(f"⏸️ [{self.bot_id}] Manual pause")
    
    def resume(self):
        self.is_paused = False
        self.auto_paused = False
        self.stable_checks = 0
        print(f"▶️ [{self.bot_id}] Manual resume")


class SidewayScanner:
    """Scan for sideway crypto coins"""
    
    def __init__(self, api_key, api_secret, use_testnet=True):
        self.use_testnet = use_testnet
        
        api_key = api_key.strip().replace(' ', '').replace('\n', '').replace('\r', '')
        api_secret = api_secret.strip().replace(' ', '').replace('\n', '').replace('\r', '')
        
        if use_testnet:
            self.client = Client(api_key, api_secret, testnet=True)
            self.client.API_URL = 'https://testnet.binancefuture.com'
        else:
            self.client = Client(api_key, api_secret)
    
    def analyze_symbol(self, symbol):
        """Analyze if a symbol is in sideway"""
        try:
            klines = self.client.futures_klines(symbol=symbol, interval='1h', limit=24)
            df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', 
                                               'close_time', 'quote_volume', 'trades', 
                                               'taker_buy_base', 'taker_buy_quote', 'ignore'])
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            
            volatility = (df['high'].max() - df['low'].min()) / df['close'].mean() * 100
            sma_short = df['close'].tail(6).mean()
            sma_long = df['close'].tail(24).mean()
            trend_strength = abs((sma_short - sma_long) / sma_long) * 100
            
            current_price = df['close'].iloc[-1]
            
            is_sideway = (trend_strength < 2 and volatility < 4)
            
            return {
                'symbol': symbol,
                'is_sideway': is_sideway,
                'volatility': volatility,
                'trend_strength': trend_strength,
                'current_price': current_price
            }
        except Exception as e:
            return None
    
    def scan_all_symbols(self, callback=None):
        """Scan all USDT futures symbols"""
        try:
            exchange_info = self.client.futures_exchange_info()
            symbols = [s['symbol'] for s in exchange_info['symbols'] 
                      if s['symbol'].endswith('USDT') and s['status'] == 'TRADING']
            
            sideway_coins = []
            total = len(symbols)
            
            for i, symbol in enumerate(symbols):
                if callback:
                    callback(i + 1, total, symbol)
                
                result = self.analyze_symbol(symbol)
                if result and result['is_sideway']:
                    sideway_coins.append(result)
                
                time.sleep(0.1)
            
            sideway_coins.sort(key=lambda x: x['volatility'])
            
            return sideway_coins
            
        except Exception as e:
            print(f"Scan error: {str(e)}")
            return []


class BotGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Binance Futures HEDGE Bot 🚀 v2.2.1 - Per-Position TP/SL")
        self.root.geometry("1200x900")
        
        self.bots = {}
        self.current_symbol = "BTCUSDT"
        self.scanner = None
        self.my_ipv4 = None
        
        atexit.register(self.cleanup_on_exit)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.setup_ui()
        self.start_summary_updates()
        self.check_my_ip()
    
    def cleanup_on_exit(self):
        """Clean up all bots on exit"""
        print("\n🗑️ Cleaning up all bots...")
        for symbol, data in list(self.bots.items()):
            bot = data.get('bot')
            if bot and bot.is_running:
                print(f"🛑 Stopping {symbol}...")
                bot.stop()
                if bot.bot_thread and bot.bot_thread.is_alive():
                    bot.bot_thread.join(timeout=5)
        print("✅ Cleanup complete")
    
    def on_closing(self):
        """Handle window close"""
        if messagebox.askokcancel("Quit", "Stop all bots and exit?"):
            self.cleanup_on_exit()
            self.root.destroy()
    
    def start_summary_updates(self):
        """Start periodic summary updates"""
        self.update_summary()
    
    def check_my_ip(self):
        """Check and display user's IPv4 address"""
        def fetch_ip():
            try:
                services = [
                    'https://api.ipify.org',
                    'https://ifconfig.me/ip',
                    'https://icanhazip.com',
                    'https://ident.me'
                ]
                
                for service in services:
                    try:
                        response = requests.get(service, timeout=5)
                        if response.status_code == 200:
                            ip = response.text.strip()
                            parts = ip.split('.')
                            if len(parts) == 4 and all(0 <= int(p) <= 255 for p in parts):
                                self.my_ipv4 = ip
                                self.root.after(0, lambda: self.update_ip_display(ip))
                                return
                    except:
                        continue
                
                self.root.after(0, lambda: self.update_ip_display(None))
            except Exception as e:
                print(f"Error fetching IP: {e}")
                self.root.after(0, lambda: self.update_ip_display(None))
        
        threading.Thread(target=fetch_ip, daemon=True).start()
    
    def update_ip_display(self, ip):
        """Update IP address display in GUI"""
        if hasattr(self, 'ip_label'):
            if ip:
                self.ip_label.config(
                    text=f"Your IPv4: {ip}",
                    foreground="green",
                    font=("Arial", 10, "bold")
                )
                self.copy_ip_button.config(state="normal")
            else:
                self.ip_label.config(
                    text="IPv4: Unable to detect",
                    foreground="red",
                    font=("Arial", 9)
                )
                self.copy_ip_button.config(state="disabled")
    
    def copy_ip_to_clipboard(self):
        """Copy IP address to clipboard"""
        if self.my_ipv4:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.my_ipv4)
            messagebox.showinfo(
                "IP Copied",
                f"✅ IP address copied!\n\n"
                f"📋 {self.my_ipv4}\n\n"
                f"Add this to your Binance API restrictions!"
            )
    
    def setup_ui(self):
        # Main notebook
        self.main_notebook = ttk.Notebook(self.root)
        self.main_notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Config tab
        config_tab = ttk.Frame(self.main_notebook)
        self.main_notebook.add(config_tab, text="⚙️ Config")
        self.setup_config_tab(config_tab)
        
        # Scanner tab
        scanner_tab = ttk.Frame(self.main_notebook)
        self.main_notebook.add(scanner_tab, text="🔍 Scan Sideway")
        self.setup_scanner_tab(scanner_tab)
        
        # Control bar
        control_bar = ttk.Frame(self.root)
        control_bar.pack(fill="x", padx=10, pady=5)
        
        # Left - Add symbol
        add_frame = ttk.LabelFrame(control_bar, text="➕ Add Symbol", padding=5)
        add_frame.pack(side="left", padx=5)
        
        add_inner = ttk.Frame(add_frame)
        add_inner.pack()
        
        ttk.Label(add_inner, text="Symbol:").pack(side="left", padx=5)
        self.new_symbol_entry = ttk.Entry(add_inner, width=15)
        self.new_symbol_entry.pack(side="left", padx=5)
        ttk.Button(add_inner, text="Add Tab", command=self.add_symbol_tab).pack(side="left", padx=5)
        
        # Right - Summary
        summary_frame = ttk.LabelFrame(control_bar, text="💰 SUMMARY", padding=5)
        summary_frame.pack(side="right", padx=5, fill="x", expand=True)
        
        summary_grid = ttk.Frame(summary_frame)
        summary_grid.pack(fill="x", padx=10)
        
        # Balance row
        balance_row = ttk.Frame(summary_grid)
        balance_row.pack(fill="x", pady=2)
        
        ttk.Label(balance_row, text="💵 Total Balance:", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        self.total_balance_label = ttk.Label(balance_row, text="$0.00", 
                                              font=("Arial", 10, "bold"), foreground="blue")
        self.total_balance_label.pack(side="left", padx=5)
        
        ttk.Label(balance_row, text="(Available:", font=("Arial", 9)).pack(side="left", padx=2)
        self.available_balance_label = ttk.Label(balance_row, text="$0.00", 
                                                  font=("Arial", 9), foreground="blue")
        self.available_balance_label.pack(side="left")
        ttk.Label(balance_row, text=")", font=("Arial", 9)).pack(side="left")
        
        # PnL row
        pnl_row = ttk.Frame(summary_grid)
        pnl_row.pack(fill="x", pady=2)
        
        ttk.Label(pnl_row, text="📊 PnL:", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        
        ttk.Label(pnl_row, text="Unrealized:", font=("Arial", 9)).pack(side="left", padx=2)
        self.unrealized_pnl_label = ttk.Label(pnl_row, text="$0.00", 
                                               font=("Arial", 9, "bold"), foreground="orange")
        self.unrealized_pnl_label.pack(side="left", padx=5)
        
        ttk.Label(pnl_row, text="Total:", font=("Arial", 9, "bold")).pack(side="left", padx=2)
        self.total_pnl_label = ttk.Label(pnl_row, text="$0.00", 
                                         font=("Arial", 10, "bold"), foreground="green")
        self.total_pnl_label.pack(side="left", padx=5)
        
        # Status row
        status_row = ttk.Frame(summary_grid)
        status_row.pack(fill="x", pady=2)
        
        ttk.Label(status_row, text="🤖", font=("Arial", 10)).pack(side="left", padx=5)
        self.active_bots_label = ttk.Label(status_row, text="Bots: 0", 
                                           font=("Arial", 9))
        self.active_bots_label.pack(side="left", padx=5)
    
    def setup_config_tab(self, parent):
        config_frame = ttk.LabelFrame(parent, text="🔑 API Configuration", padding=10)
        config_frame.pack(fill="x", padx=10, pady=5)
        
        # IP Display
        ip_frame = ttk.Frame(config_frame)
        ip_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        
        ttk.Label(ip_frame, text="🌐", font=("Arial", 12)).pack(side="left", padx=5)
        self.ip_label = ttk.Label(ip_frame, text="Checking your IPv4...", 
                                   font=("Arial", 9), foreground="gray")
        self.ip_label.pack(side="left", padx=5)
        
        self.copy_ip_button = ttk.Button(ip_frame, text="📋 Copy IP", 
                                          command=self.copy_ip_to_clipboard,
                                          width=12, state="disabled")
        self.copy_ip_button.pack(side="left", padx=5)
        
        ttk.Button(ip_frame, text="🔄 Refresh IP", 
                  command=self.check_my_ip, width=12).pack(side="left", padx=5)
        
        # Separator
        ttk.Separator(config_frame, orient='horizontal').grid(row=1, column=0, columnspan=3, sticky="ew", pady=5)
        
        # API Key & Secret
        ttk.Label(config_frame, text="API Key:").grid(row=2, column=0, sticky="w", pady=2)
        self.api_key_entry = ttk.Entry(config_frame, width=60)
        self.api_key_entry.grid(row=2, column=1, pady=2, columnspan=2, sticky="ew")
        
        ttk.Label(config_frame, text="API Secret:").grid(row=3, column=0, sticky="w", pady=2)
        self.api_secret_entry = ttk.Entry(config_frame, width=60, show="•")
        self.api_secret_entry.grid(row=3, column=1, pady=2, columnspan=2, sticky="ew")
        
        # Testnet checkbox
        self.use_testnet = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="🧪 Use Testnet (Uncheck for REAL ⚠️)", 
                       variable=self.use_testnet, 
                       command=self.toggle_testnet_warning).grid(row=4, column=1, sticky="w", pady=5)
        
        self.mode_warning_label = ttk.Label(config_frame, text="Mode: TESTNET (Safe) 🧪", 
                                            font=("Arial", 10, "bold"), foreground="green")
        self.mode_warning_label.grid(row=5, column=1, sticky="w", pady=2)
        
        # Test Button
        ttk.Button(config_frame, text="🔌 Test Connection", 
                  command=self.test_api_connection, width=20).grid(row=6, column=1, sticky="w", pady=10)
        
        # Instructions
        info_frame = ttk.LabelFrame(parent, text="📖 v2.2.1 - PER-POSITION TP/SL ADDED", padding=10)
        info_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        instructions = """
🆕 VERSION 2.2.1 - PER-POSITION TAKE PROFIT & STOP LOSS:
========================================================
✅ All v2.2.0 features (GUI, multi-tab, scanner)
✅ AUTO CLOSE positions when TP/SL hit (NEW!)
✅ Per-position trailing stop (NEW!)
✅ Smart position management (NEW!)
✅ Optimized for small capital (10-100 USD)

🎯 NEW: PER-POSITION TP/SL:
===========================
Each position now has its own TP/SL that auto-closes when triggered!

For Capital $10-20:
  • Position TP: +2.0% ✅ (closes position)
  • Position SL: -1.0% ❌ (closes position)
  • Trailing: 0.8% 📉
  • Risk:Reward = 1:2.0

For Capital $20-50:
  • Position TP: +2.5% ✅
  • Position SL: -1.5% ❌
  • Trailing: 1.0% 📉
  • Risk:Reward = 1:1.67

For Capital $50-100:
  • Position TP: +3.0% ✅
  • Position SL: -2.0% ❌
  • Trailing: 1.5% 📉
  • Risk:Reward = 1:1.5

For Capital $100-500:
  • Position TP: +3.5% ✅
  • Position SL: -2.5% ❌
  • Trailing: 1.8% 📉

For Capital $500-1000:
  • Position TP: +4.0% ✅
  • Position SL: -2.5% ❌
  • Trailing: 2.0% 📉

For Capital $1000+:
  • Position TP: +5.0% ✅
  • Position SL: -3.0% ❌
  • Trailing: 2.5% 📉

🔥 HOW IT WORKS:
================
1. Bot places grid orders as usual
2. When order fills → position opens
3. Bot monitors position PnL every 30 seconds
4. If PnL reaches +TP% → AUTO CLOSE position ✅
5. If PnL drops to -SL% → AUTO CLOSE position ❌
6. If PnL in profit + drops by Trailing% → AUTO CLOSE 📉
7. Position closed → grid order refilled automatically

💡 KEY BENEFITS:
================
• Lock profits automatically
• Limit losses per position
• No manual intervention needed
• Each position independent
• Grid continues after close

📊 POSITION MONITORING:
======================
Bot displays real-time status:
🟢 LONG | PnL: +2.34% ($0.00234) | Peak: $0.00350 | TP:3% SL:-2% Trail:1.5%
🔴 SHORT | PnL: -1.12% ($-0.00112) | Peak: $0.00050 | TP:3% SL:-2% Trail:1.5%

When triggered:
✅ TAKE PROFIT (2.45% >= 2.0%) → Position closed!
🛑 STOP LOSS (-2.03% <= -2.0%) → Position closed!
📉 TRAILING STOP (1.52% drop from peak) → Position closed!

⚖️ RISK MANAGEMENT:
==================
TWO LEVELS of protection:

1. PER-POSITION (NEW!):
   • Closes individual positions
   • Fast reaction (30s check)
   • Protects each trade

2. BOT-LEVEL (Existing):
   • Stops entire bot
   • Stop Loss: 3-5%
   • Take Profit: 5-10%
   • Max Drawdown: 10-15%

🚀 QUICK START:
===============
1. Enter API Key + Secret
2. Click "🔌 Test Connection"
3. Add symbol (BTCUSDT for small capital)
4. Set capital: $10-100
5. Enable "🔄 Auto Grid Count"
6. Click "🔧 Initialize"
   → Watch auto-optimization!
   → TP/SL % set automatically!
7. Click "▶️ START"
8. Monitor positions auto-closing!

💰 EXAMPLE WITH $50 CAPITAL:
============================
Settings auto-optimized:
• Grid: 6 levels
• Range: 1.5%
• Leverage: 7x
• Position TP: +2.5% ✅
• Position SL: -1.5% ❌
• Trailing: 1.0% 📉

Scenario:
1. Grid order fills → LONG position opened
2. Entry: $50,000
3. Price rises to $51,250 → +2.5% profit
4. Bot auto-closes: ✅ "TAKE PROFIT!"
5. Realized: +$0.875 (after fees)
6. Grid refills automatically
7. Repeat!

Required win rate: >37.5% to break even
With 50% win rate → steady profit! 📈

⚠️ IMPORTANT:
=============
• TP/SL works ON EACH POSITION
• Does NOT stop the bot
• Grid continues after close
• Multiple positions can trigger simultaneously
• Use TESTNET first to see it work!

🔧 ADVANCED:
============
• Each tab independent
• Different TP/SL per symbol
• Real-time monitoring
• Clean shutdown on exit
• Thread-safe execution

📈 RECOMMENDED WORKFLOW:
=======================
1. Start with $10-20 on TESTNET
2. Watch positions auto-close
3. See profit/loss management
4. Understand timing
5. Move to REAL when confident!

🎓 LEARNING TIP:
================
Set very tight TP/SL on TESTNET (TP:1% SL:0.5%)
to see frequent auto-closes and learn the system!
        """
        
        info_text = tk.Text(info_frame, height=25, width=80, wrap="word", font=("Arial", 9))
        info_text.insert("1.0", instructions)
        info_text.config(state="disabled")
        
        scrollbar = ttk.Scrollbar(info_frame, orient="vertical", command=info_text.yview)
        info_text.configure(yscrollcommand=scrollbar.set)
        
        info_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")
    
    def test_api_connection(self):
        """Test API connection"""
        api_key = self.api_key_entry.get().strip()
        api_secret = self.api_secret_entry.get().strip()
        
        if not api_key or not api_secret:
            messagebox.showerror("Error", "Please enter API Key & Secret!")
            return
        
        test_window = tk.Toplevel(self.root)
        test_window.title("Testing...")
        test_window.geometry("400x200")
        test_window.transient(self.root)
        test_window.grab_set()
        
        ttk.Label(test_window, text="🔍 Testing API...", 
                 font=("Arial", 12, "bold")).pack(pady=20)
        
        progress = ttk.Progressbar(test_window, mode='indeterminate', length=300)
        progress.pack(pady=10)
        progress.start()
        
        status_label = ttk.Label(test_window, text="Connecting...", 
                                font=("Arial", 10))
        status_label.pack(pady=10)
        
        def test_thread():
            try:
                use_testnet = self.use_testnet.get()
                
                clean_key = api_key.replace(' ', '').replace('\n', '').replace('\r', '')
                clean_secret = api_secret.replace(' ', '').replace('\n', '').replace('\r', '')
                
                if use_testnet:
                    client = Client(clean_key, clean_secret, testnet=True)
                    client.API_URL = 'https://testnet.binancefuture.com'
                    mode_text = "TESTNET"
                else:
                    client = Client(clean_key, clean_secret)
                    mode_text = "REAL BINANCE"
                
                server_time = client.get_server_time()
                account = client.futures_account()
                
                progress.stop()
                test_window.destroy()
                
                balance = 0
                for asset in account['assets']:
                    if asset['asset'] == 'USDT':
                        balance = float(asset['walletBalance'])
                        break
                
                messagebox.showinfo(
                    "✅ Success!",
                    f"Connection to {mode_text} successful!\n\n"
                    f"📊 Balance: ${balance:.2f} USDT\n"
                    f"✅ API key is valid!\n"
                    f"✅ Futures enabled!"
                )
                
            except Exception as e:
                progress.stop()
                test_window.destroy()
                messagebox.showerror("❌ Error", f"Connection failed:\n\n{str(e)}")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def toggle_testnet_warning(self):
        """Toggle testnet warning"""
        if self.use_testnet.get():
            self.mode_warning_label.config(text="Mode: TESTNET (Safe) 🧪", foreground="green")
        else:
            result = messagebox.askquestion(
                "⚠️ WARNING",
                "Switch to REAL TRADING?\n\nThis uses YOUR REAL MONEY!\n\nContinue?",
                icon='warning'
            )
            if result == 'yes':
                self.mode_warning_label.config(text="Mode: REAL BINANCE ⚠️💰", foreground="red")
            else:
                self.use_testnet.set(True)
                self.mode_warning_label.config(text="Mode: TESTNET (Safe) 🧪", foreground="green")
    
    def setup_scanner_tab(self, parent):
        scanner_frame = ttk.LabelFrame(parent, text="🔍 Scan Sideway Cryptos", padding=10)
        scanner_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        control_frame = ttk.Frame(scanner_frame)
        control_frame.pack(fill="x", pady=5)
        
        ttk.Button(control_frame, text="🔍 Scan All Futures", 
                  command=self.start_scan, width=20).pack(side="left", padx=5)
        
        self.scan_progress_label = ttk.Label(control_frame, text="Ready...")
        self.scan_progress_label.pack(side="left", padx=10)
        
        results_frame = ttk.Frame(scanner_frame)
        results_frame.pack(fill="both", expand=True, pady=5)
        
        columns = ('symbol', 'price', 'volatility', 'trend', 'status')
        self.scanner_tree = ttk.Treeview(results_frame, columns=columns, show='headings', height=20)
        
        self.scanner_tree.heading('symbol', text='Symbol')
        self.scanner_tree.heading('price', text='Price')
        self.scanner_tree.heading('volatility', text='Volatility %')
        self.scanner_tree.heading('trend', text='Trend %')
        self.scanner_tree.heading('status', text='Status')
        
        self.scanner_tree.column('symbol', width=120)
        self.scanner_tree.column('price', width=120)
        self.scanner_tree.column('volatility', width=100)
        self.scanner_tree.column('trend', width=100)
        self.scanner_tree.column('status', width=150)
        
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.scanner_tree.yview)
        self.scanner_tree.configure(yscrollcommand=scrollbar.set)
        
        self.scanner_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.scanner_tree.bind('<Double-1>', self.add_from_scanner)
        
        info_label = ttk.Label(scanner_frame, 
                               text="💡 Double-click to add symbol", 
                               font=("Arial", 9, "italic"))
        info_label.pack(pady=5)
    
    def start_scan(self):
        api_key = self.api_key_entry.get().strip()
        api_secret = self.api_secret_entry.get().strip()
        
        if not api_key or not api_secret:
            messagebox.showerror("Error", "Enter API Key & Secret first!")
            return
        
        for item in self.scanner_tree.get_children():
            self.scanner_tree.delete(item)
        
        self.scan_progress_label.config(text="Scanning... 0/0")
        
        def scan_thread():
            try:
                use_testnet = self.use_testnet.get()
                self.scanner = SidewayScanner(api_key, api_secret, use_testnet)
                
                def update_progress(current, total, symbol):
                    self.scan_progress_label.config(text=f"Scanning... {current}/{total} - {symbol}")
                
                results = self.scanner.scan_all_symbols(callback=update_progress)
                self.root.after(0, lambda: self.display_scan_results(results))
                
            except Exception as e:
                messagebox.showerror("Error", f"Scan error: {str(e)}")
                self.scan_progress_label.config(text="Scan error!")
        
        threading.Thread(target=scan_thread, daemon=True).start()
    
    def display_scan_results(self, results):
        for item in self.scanner_tree.get_children():
            self.scanner_tree.delete(item)
        
        if not results:
            self.scan_progress_label.config(text="No sideway coins found!")
            return
        
        for coin in results:
            status = "✅ SIDEWAY - Good for Grid"
            self.scanner_tree.insert('', 'end', values=(
                coin['symbol'],
                f"${coin['current_price']:,.2f}",
                f"{coin['volatility']:.2f}%",
                f"{coin['trend_strength']:.2f}%",
                status
            ), tags=('good',))
        
        self.scanner_tree.tag_configure('good', foreground='green')
        self.scan_progress_label.config(text=f"✅ Found {len(results)} sideway coins!")
    
    def add_from_scanner(self, event):
        selection = self.scanner_tree.selection()
        if not selection:
            return
        
        item = self.scanner_tree.item(selection[0])
        symbol = item['values'][0]
        
        if symbol in self.bots:
            messagebox.showinfo("Info", f"{symbol} already exists!")
            return
        
        symbol_tab = ttk.Frame(self.main_notebook)
        tab_index = self.main_notebook.index("end")
        self.main_notebook.add(symbol_tab, text=f"📊 {symbol}")
        
        self.create_symbol_interface(symbol_tab, symbol, tab_index)
        messagebox.showinfo("Success", f"Added {symbol}!")
    
    def add_symbol_tab(self):
        symbol = self.new_symbol_entry.get().strip().upper()
        if not symbol:
            messagebox.showwarning("Warning", "Enter symbol!")
            return
        
        if symbol in self.bots:
            messagebox.showinfo("Info", f"{symbol} already exists!")
            return
        
        symbol_tab = ttk.Frame(self.main_notebook)
        tab_index = self.main_notebook.index("end")
        self.main_notebook.add(symbol_tab, text=f"📊 {symbol}")
        
        self.create_symbol_interface(symbol_tab, symbol, tab_index)
        self.new_symbol_entry.delete(0, 'end')
    
    def create_symbol_interface(self, parent, symbol, tab_index):
        # Header
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(header_frame, text=f"🎯 {symbol} Trading", 
                 font=("Arial", 12, "bold")).pack(side="left")
        
        ttk.Button(header_frame, text="❌ Close Tab", 
                  command=lambda: self.close_symbol_tab(symbol, tab_index),
                  width=12).pack(side="right", padx=5)
        
        # Settings
        settings_frame = ttk.LabelFrame(parent, text="⚙️ Settings - HEDGE MODE v2.2.1 (Per-Position TP/SL)", padding=10)
        settings_frame.pack(fill="x", padx=10, pady=5)
        
        settings_grid = ttk.Frame(settings_frame)
        settings_grid.pack(fill="x")
        
        # Row 1
        ttk.Label(settings_grid, text="Capital (USDT):").grid(row=0, column=0, sticky="w", pady=2, padx=5)
        capital_entry = ttk.Entry(settings_grid, width=12)
        capital_entry.insert(0, "50")
        capital_entry.grid(row=0, column=1, sticky="w", pady=2)
        
        ttk.Label(settings_grid, text="Leverage:").grid(row=0, column=2, sticky="w", pady=2, padx=5)
        leverage_entry = ttk.Entry(settings_grid, width=12)
        leverage_entry.insert(0, "10")
        leverage_entry.grid(row=0, column=3, sticky="w", pady=2)
        
        ttk.Label(settings_grid, text="Bot Stop Loss (%):").grid(row=0, column=4, sticky="w", pady=2, padx=5)
        stop_loss_entry = ttk.Entry(settings_grid, width=12)
        stop_loss_entry.insert(0, "3")
        stop_loss_entry.grid(row=0, column=5, sticky="w", pady=2)
        
        # Row 2
        ttk.Label(settings_grid, text="Grid Count:").grid(row=1, column=0, sticky="w", pady=2, padx=5)
        grid_count_entry = ttk.Entry(settings_grid, width=12)
        grid_count_entry.insert(0, "8")
        grid_count_entry.grid(row=1, column=1, sticky="w", pady=2)
        
        ttk.Label(settings_grid, text="Range (%):").grid(row=1, column=2, sticky="w", pady=2, padx=5)
        grid_range_entry = ttk.Entry(settings_grid, width=12)
        grid_range_entry.insert(0, "2")
        grid_range_entry.grid(row=1, column=3, sticky="w", pady=2)
        
        ttk.Label(settings_grid, text="Max Orders/Side:").grid(row=1, column=4, sticky="w", pady=2, padx=5)
        max_orders_entry = ttk.Entry(settings_grid, width=12)
        max_orders_entry.insert(0, "4")
        max_orders_entry.grid(row=1, column=5, sticky="w", pady=2)
        
        # Row 3 - Features
        auto_grid_var = tk.BooleanVar(value=True)
        dynamic_grid_var = tk.BooleanVar(value=True)
        auto_pause_var = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(settings_grid, text="🔄 Dynamic Grid", 
                       variable=dynamic_grid_var).grid(row=2, column=0, columnspan=2, sticky="w", pady=2)
        ttk.Checkbutton(settings_grid, text="🤖 Auto Pause/Resume", 
                       variable=auto_pause_var).grid(row=2, column=2, columnspan=2, sticky="w", pady=2)
        ttk.Checkbutton(settings_grid, text="📊 Auto Grid Count (Recommended)", 
                       variable=auto_grid_var).grid(row=2, column=4, columnspan=2, sticky="w", pady=2)
        
        # Control
        control_frame = ttk.LabelFrame(parent, text=f"🎮 {symbol} Control", padding=10)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(control_frame, text="🔧 Initialize", command=lambda: self.initialize_bot(symbol), width=12).pack(side="left", padx=5)
        ttk.Button(control_frame, text="▶️ START", command=lambda: self.start_bot(symbol), width=12).pack(side="left", padx=5)
        ttk.Button(control_frame, text="⏸️ PAUSE", command=lambda: self.pause_bot(symbol), width=12).pack(side="left", padx=5)
        ttk.Button(control_frame, text="⏹️ STOP", command=lambda: self.stop_bot(symbol), width=12).pack(side="left", padx=5)
        ttk.Button(control_frame, text="🔄 UPDATE", command=lambda: self.manual_update(symbol), width=12).pack(side="left", padx=5)
        
        # Info
        info_frame = ttk.LabelFrame(parent, text="📊 Information", padding=10)
        info_frame.pack(fill="x", padx=10, pady=5)
        
        info_grid = ttk.Frame(info_frame)
        info_grid.pack(fill="x")
        
        status_label = ttk.Label(info_grid, text="Status: Not initialized", font=("Arial", 10, "bold"))
        status_label.grid(row=0, column=0, sticky="w", padx=10, pady=2)
        
        market_label = ttk.Label(info_grid, text="Market: --", font=("Arial", 9))
        market_label.grid(row=0, column=1, sticky="w", padx=10, pady=2)
        
        mode_label = ttk.Label(info_grid, text="Mode: HEDGE ⚖️ + Per-Position TP/SL 🎯", font=("Arial", 9, "bold"), foreground="purple")
        mode_label.grid(row=0, column=2, sticky="w", padx=10, pady=2)
        
        price_frame = ttk.LabelFrame(info_grid, text="💰 Current Price", padding=5)
        price_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=5)
        
        price_label = ttk.Label(price_frame, text="--", font=("Arial", 16, "bold"), foreground="blue")
        price_label.pack()
        
        balance_label = ttk.Label(info_grid, text="Balance: --", font=("Arial", 9))
        balance_label.grid(row=2, column=0, sticky="w", padx=10, pady=2)
        
        pnl_label = ttk.Label(info_grid, text="PnL: --", font=("Arial", 9))
        pnl_label.grid(row=2, column=1, sticky="w", padx=10, pady=2)
        
        # Data Notebook
        data_notebook = ttk.Notebook(parent)
        data_notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Positions tab
        pos_frame = ttk.Frame(data_notebook)
        data_notebook.add(pos_frame, text="📈 Positions")
        
        pos_tree = ttk.Treeview(pos_frame, columns=('symbol', 'side', 'pos_side', 'amount', 'entry', 'pnl'), 
                                show='headings', height=5)
        pos_tree.heading('symbol', text='Symbol')
        pos_tree.heading('side', text='Side')
        pos_tree.heading('pos_side', text='Position')
        pos_tree.heading('amount', text='Amount')
        pos_tree.heading('entry', text='Entry')
        pos_tree.heading('pnl', text='PnL')
        pos_tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Orders tab
        orders_frame = ttk.Frame(data_notebook)
        data_notebook.add(orders_frame, text="⏳ Open Orders")
        
        orders_paned = ttk.PanedWindow(orders_frame, orient='horizontal')
        orders_paned.pack(fill="both", expand=True, padx=5, pady=5)
        
        buy_frame = ttk.LabelFrame(orders_paned, text="🟢 BUY LONG", padding=5)
        orders_paned.add(buy_frame)
        
        buy_tree = ttk.Treeview(buy_frame, columns=('price', 'qty', 'time'), show='headings', height=8)
        buy_tree.heading('price', text='Price')
        buy_tree.heading('qty', text='Quantity')
        buy_tree.heading('time', text='Time')
        buy_tree.pack(fill="both", expand=True)
        
        sell_frame = ttk.LabelFrame(orders_paned, text="🔴 SELL SHORT", padding=5)
        orders_paned.add(sell_frame)
        
        sell_tree = ttk.Treeview(sell_frame, columns=('price', 'qty', 'time'), show='headings', height=8)
        sell_tree.heading('price', text='Price')
        sell_tree.heading('qty', text='Quantity')
        sell_tree.heading('time', text='Time')
        sell_tree.pack(fill="both", expand=True)
        
        # Filled Orders tab
        filled_frame = ttk.Frame(data_notebook)
        data_notebook.add(filled_frame, text="✅ Filled")
        
        filled_tree = ttk.Treeview(filled_frame, columns=('side', 'price', 'qty', 'pnl', 'time'), 
                                   show='headings', height=10)
        filled_tree.heading('side', text='Side')
        filled_tree.heading('price', text='Price')
        filled_tree.heading('qty', text='Qty')
        filled_tree.heading('pnl', text='PnL')
        filled_tree.heading('time', text='Time')
        filled_tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Store widgets
        if symbol not in self.bots:
            self.bots[symbol] = {
                'bot': None,
                'tab_index': tab_index,
                'widgets': {
                    'status': status_label,
                    'market': market_label,
                    'mode': mode_label,
                    'price': price_label,
                    'balance': balance_label,
                    'pnl': pnl_label,
                    'pos_tree': pos_tree,
                    'buy_tree': buy_tree,
                    'sell_tree': sell_tree,
                    'filled_tree': filled_tree,
                    'capital_entry': capital_entry,
                    'leverage_entry': leverage_entry,
                    'stop_loss_entry': stop_loss_entry,
                    'grid_count_entry': grid_count_entry,
                    'grid_range_entry': grid_range_entry,
                    'auto_grid_var': auto_grid_var,
                    'max_orders_entry': max_orders_entry,
                    'dynamic_grid_var': dynamic_grid_var,
                    'auto_pause_var': auto_pause_var
                }
            }
        
        self.update_symbol_display(symbol)
    
    def close_symbol_tab(self, symbol, tab_index):
        """Close a symbol tab"""
        if symbol in self.bots:
            bot = self.bots[symbol].get('bot')
            if bot and bot.is_running:
                result = messagebox.askyesno("Confirm", 
                                            f"Bot {symbol} is running!\nStop and close?")
                if result:
                    bot.stop()
                    if bot.bot_thread and bot.bot_thread.is_alive():
                        bot.bot_thread.join(timeout=5)
                else:
                    return
            
            del self.bots[symbol]
            self.main_notebook.forget(tab_index)
            messagebox.showinfo("Success", f"Closed {symbol}")
    
    def update_symbol_display(self, symbol):
        if symbol not in self.bots:
            return
        
        bot_data = self.bots[symbol]
        bot = bot_data.get('bot')
        widgets = bot_data['widgets']
        
        if bot:
            widgets['price'].config(text=f"${bot.current_price:.2f}")
            widgets['balance'].config(text=f"Balance: ${bot.balance:.2f}")
            
            pnl_color = "green" if bot.pnl >= 0 else "red"
            pnl_sign = "+" if bot.pnl >= 0 else ""
            widgets['pnl'].config(text=f"PnL: {pnl_sign}${bot.pnl:.2f}", foreground=pnl_color)
            
            widgets['market'].config(text=f"Market: {bot.market_state}")
            
            self.update_tables(symbol)
        
        self.root.after(2000, lambda: self.update_symbol_display(symbol))
    
    def initialize_bot(self, symbol):
        api_key = self.api_key_entry.get().strip()
        api_secret = self.api_secret_entry.get().strip()
        
        if not api_key or not api_secret:
            messagebox.showerror("Error", "Enter API Key & Secret!")
            return
        
        try:
            widgets = self.bots[symbol]['widgets']
            use_testnet = self.use_testnet.get()
            
            bot = BinanceFuturesBot(api_key, api_secret, use_testnet, bot_id=symbol)
            bot.symbol = symbol
            bot.leverage = int(widgets['leverage_entry'].get())
            bot.capital = float(widgets['capital_entry'].get())
            bot.grid_count = int(widgets['grid_count_entry'].get())
            bot.grid_range_percent = float(widgets['grid_range_entry'].get())
            bot.auto_grid = widgets['auto_grid_var'].get()
            bot.stop_loss_percent = float(widgets['stop_loss_entry'].get())
            bot.max_open_orders_per_side = int(widgets['max_orders_entry'].get())
            bot.enable_dynamic_grid = widgets['dynamic_grid_var'].get()
            bot.enable_auto_pause_resume = widgets['auto_pause_var'].get()
            
            success, message = bot.initialize()
            
            if success:
                self.bots[symbol]['bot'] = bot
                mode = "Testnet 🧪" if use_testnet else "Real 💰"
                
                if bot.is_small_capital:
                    widgets['status'].config(
                        text=f"Status: Ready ✅ ({mode}) 💡 Small Capital + Per-Position TP/SL", 
                        foreground="green"
                    )
                else:
                    widgets['status'].config(text=f"Status: Ready ✅ ({mode}) 🎯 Per-Position TP/SL Active", foreground="green")
                
                messagebox.showinfo("Success", 
                    f"{message}\n\n"
                    f"✅ {symbol} bot initialized!\n"
                    f"🔒 Grid prices LOCKED (stable)\n"
                    f"🎯 Per-Position TP/SL: {bot.position_tp_percent}% / -{bot.position_sl_percent}%\n"
                    f"📉 Trailing Stop: {bot.position_trailing_percent}%\n"
                    f"🤖 Independent thread ready\n"
                    f"⏱️ Cooldowns active (5min rebalance, 3min pause)\n"
                    f"{'💡 Small capital mode active!' if bot.is_small_capital else ''}")
            else:
                messagebox.showerror("Error", message)
                
        except Exception as e:
            messagebox.showerror("Error", f"Cannot initialize: {str(e)}")
    
    def start_bot(self, symbol):
        if symbol not in self.bots or not self.bots[symbol]['bot']:
            messagebox.showwarning("Warning", "Initialize bot first!")
            return
        
        bot = self.bots[symbol]['bot']
        bot.start()
        self.bots[symbol]['widgets']['status'].config(text=f"Status: Running 🟢 [{symbol}] 🎯 Auto TP/SL Active", foreground="green")
        messagebox.showinfo("Started", 
            f"✅ {symbol} bot started!\n"
            f"🔒 Grid stable with cooldowns!\n"
            f"🎯 Positions will auto-close at:\n"
            f"   • Take Profit: +{bot.position_tp_percent}%\n"
            f"   • Stop Loss: -{bot.position_sl_percent}%\n"
            f"   • Trailing: {bot.position_trailing_percent}%")
    
    def pause_bot(self, symbol):
        if symbol in self.bots and self.bots[symbol]['bot']:
            self.bots[symbol]['bot'].pause()
            self.bots[symbol]['widgets']['status'].config(text=f"Status: Paused ⏸️ [{symbol}]", foreground="orange")
    
    def stop_bot(self, symbol):
        if symbol in self.bots and self.bots[symbol]['bot']:
            result = messagebox.askyesno("Confirm", 
                                        f"Stop {symbol} and close all positions?")
            if result:
                bot = self.bots[symbol]['bot']
                bot.stop()
                if bot.bot_thread and bot.bot_thread.is_alive():
                    bot.bot_thread.join(timeout=5)
                self.bots[symbol]['widgets']['status'].config(text=f"Status: Stopped ⏹️ [{symbol}]", foreground="red")
                messagebox.showinfo("Info", f"✅ Stopped {symbol}!\n🗑️ Cache cleaned")
    
    def manual_update(self, symbol):
        if symbol in self.bots and self.bots[symbol]['bot']:
            bot = self.bots[symbol]['bot']
            bot.update_price()
            bot.calculate_pnl()
            bot.get_positions()
            bot.get_open_orders()
            bot.get_filled_orders()
            self.update_tables(symbol)
    
    def update_tables(self, symbol):
        if symbol not in self.bots or not self.bots[symbol]['bot']:
            return
        
        bot = self.bots[symbol]['bot']
        widgets = self.bots[symbol]['widgets']
        
        # Positions
        pos_tree = widgets['pos_tree']
        for item in pos_tree.get_children():
            pos_tree.delete(item)
        
        for pos in bot.positions:
            pnl_color = 'green' if pos['unrealized_pnl'] >= 0 else 'red'
            pos_tree.insert('', 'end', values=(
                pos['symbol'],
                pos['side'],
                pos.get('position_side', 'BOTH'),
                f"{pos['amount']:.3f}",
                f"${pos['entry_price']:.2f}",
                f"${pos['unrealized_pnl']:.2f}"
            ), tags=(pnl_color,))
        
        pos_tree.tag_configure('green', foreground='green')
        pos_tree.tag_configure('red', foreground='red')
        
        # Open orders
        buy_tree = widgets['buy_tree']
        sell_tree = widgets['sell_tree']
        
        for item in buy_tree.get_children():
            buy_tree.delete(item)
        for item in sell_tree.get_children():
            sell_tree.delete(item)
        
        for order in bot.open_orders:
            if order['position_side'] == 'LONG':
                tree = buy_tree
            else:
                tree = sell_tree
                
            tree.insert('', 'end', values=(
                f"${order['price']:.2f}",
                f"{order['quantity']:.3f}",
                order['time']
            ))
        
        # Filled orders
        filled_tree = widgets['filled_tree']
        for item in filled_tree.get_children():
            filled_tree.delete(item)
        
        for trade in bot.filled_orders[-20:]:
            pnl_color = 'green' if trade['realized_pnl'] >= 0 else 'red'
            filled_tree.insert('', 'end', values=(
                trade['side'],
                f"${trade['price']:.2f}",
                f"{trade['quantity']:.3f}",
                f"${trade['realized_pnl']:.2f}",
                trade['time']
            ), tags=(pnl_color,))
        
        filled_tree.tag_configure('green', foreground='green')
        filled_tree.tag_configure('red', foreground='red')
    
    def update_summary(self):
        """Update summary"""
        total_balance = 0
        total_available = 0
        total_pnl = 0
        active_count = 0
        
        try:
            first_bot = None
            for symbol, data in self.bots.items():
                bot = data.get('bot')
                if bot:
                    first_bot = bot
                    break
            
            if first_bot:
                account = first_bot.client.futures_account()
                
                for asset in account['assets']:
                    if asset['asset'] == 'USDT':
                        total_balance = float(asset['walletBalance'])
                        total_available = float(asset['availableBalance'])
                        break
                
                total_pnl = float(account['totalUnrealizedProfit'])
                
                for symbol, data in self.bots.items():
                    bot = data.get('bot')
                    if bot and bot.is_running:
                        active_count += 1
        except Exception as e:
            print(f"Error update summary: {e}")
        
        if total_balance > 0:
            self.total_balance_label.config(text=f"${total_balance:.2f}")
            self.available_balance_label.config(text=f"${total_available:.2f}")
            
            pnl_color = "green" if total_pnl >= 0 else "red"
            pnl_sign = "+" if total_pnl >= 0 else ""
            self.unrealized_pnl_label.config(text=f"{pnl_sign}${total_pnl:.2f}", foreground=pnl_color)
            self.total_pnl_label.config(text=f"{pnl_sign}${total_pnl:.2f}", foreground=pnl_color)
        
        total_bots = len([b for b in self.bots.values() if b.get('bot')])
        if total_bots > 0:
            self.active_bots_label.config(text=f"{active_count}/{total_bots} running")
        else:
            self.active_bots_label.config(text="No bots")
        
        self.root.after(2000, self.update_summary)
    
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = BotGUI()
    app.run()