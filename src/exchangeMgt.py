import requests
import time
import hashlib
import hmac
import uuid
import enum
import ccxt
import json

class CustomExchange:
    def __init__(self, exchange_name) -> None:
        self.exchange: ccxt.Exchange = None
        self.exchange_name = exchange_name
        pass

    def get_exchange(self, apiKey='', secret='', sandbox=False, demoaccount=False):
        try:
            exchange = getattr(ccxt, self.exchange_name)
            self.exchange = exchange({
                'apiKey':apiKey,
                'secret':secret
            })
            
            if sandbox:
                self.exchange.set_sandbox_mode(sandbox)

            if self.exchange_name == 'bybit':
                bybitCustom = BybitExchangeCustoms(apiKey, secret, sandbox, demoaccount)
                if demoaccount:
                    self.exchange:ccxt.bybit = ccxt.bybit()
                    self.exchange.create_order = bybitCustom.CreateOrder
                    self.exchange.cancel_all_orders = bybitCustom.CancelAllOrder
            else:
                self.exchange.check_required_credentials()
            markets = self.exchange.load_markets()
            return self.exchange, markets
        except Exception as raised_exception:
            if self.exchange_name=='bybit':
                print(str(raised_exception))
                return self.exchange, self.exchange.markets
            else:
                raise raised_exception


class BybitExchangeCustoms:
    def __init__(self, apikey, apisecret, testnet: bool=False, isDemo: bool=False, **kwargs) -> None:
        self.testnet_uri = 'https://api-testnet.bybit.com'
        self.mainnet_uri = 'https://api.bybit.com'
        self.demo_uri  = 'https://api-demo.bybit.com'

        self.api_key = apikey
        self.api_secret = apisecret
        self.recv_window = str(kwargs.get('recv_window', 10000))
        self.time_stamp = ""
        self.client = requests.Session()

        self.account_type = str(kwargs.get('accountType', 'UNIFIED')).upper()

        self.main_url = self.mainnet_uri

        if testnet:
            self.main_url = self.testnet_uri
        elif isDemo:
            self.main_url = self.demo_uri

        ##using v5 api
        self.order_create_endpoint = "/v5/order/create"
        self.order_cancel_all_endpoint = "/v5/order/cancel-all"
        self.GetBalance()

    def SignParameters(self, payload):
        param_str= str(self.time_stamp) + self.api_key + self.recv_window + payload
        hash = hmac.new(bytes(self.api_secret, "utf-8"), param_str.encode("utf-8"),hashlib.sha256)
        signature = hash.hexdigest()
        return signature
    
    def GetBalance(self):
        balanceendpoint = '/v5/account/wallet-balance'
        parameters = 'accountType={}&coin=USDT'.format(self.account_type)
        signature = self.SignParameters(parameters)
        response = self.HTTP_Request(balanceendpoint, 'GET', parameters,'check')
        print("Account info: ", response)

    def HTTP_Request(self, endPoint,method,payload,Info):
        self.time_stamp=str(int(time.time() * 10 ** 3))
        signature=self.SignParameters(payload)
        headers = {
            'X-BAPI-API-KEY': self.api_key,
            'X-BAPI-SIGN': signature,
            'X-BAPI-SIGN-TYPE': '2',
            'X-BAPI-TIMESTAMP': self.time_stamp,
            'X-BAPI-RECV-WINDOW': self.recv_window,
            'Content-Type': 'application/json'
        }
        if(method=="POST"):
            response = self.client.request(method, self.main_url+endPoint, headers=headers, data=payload)
        else:
            response = self.client.request(method, self.main_url+endPoint+"?"+payload, headers=headers)

        return (response.text)

    def CreateOrder(
            self,
            symbol,
            type,
            side,
            amount,
            price,
            params={}
        ):

        orderLinkId =uuid.uuid4().hex
        positionIdx = 1 if side=='buy' else 2

        precision = float(params.get('precision',2))
        quantity = int((float(amount)/float(price))/precision)*precision

        reduceOnly = bool(params.get('reduceOnly',False))
        if reduceOnly:
            positionIdx = 1 if side=='sell' else 2
            reason = params.get('reason','None')
            if reason=='takeProfit':
                triggerDirection = 1 if side=='sell' else 2
            elif reason=='stopLoss':
                triggerDirection = 2 if side=='sell' else 1
            elif reason=='close':
                pass
            else:
                print('you need to pass a reason for this order.')

        side = side.lower().capitalize()
        type = type.lower().capitalize()

        urlparams = "{"
        urlparams += '"category":"linear",'
        urlparams += '"symbol" : "'+symbol+'",'
        urlparams += '"side":"'+side+'",'
        urlparams += '"positionIdx" :"'+str(positionIdx)+'",'
        urlparams += '"orderType":"'+type+'",'
        urlparams += '"timeInForce": "'+params.get("timeInForce","GTC")+'",'
        urlparams += '"price": "'+str(price)+'",'

        if reduceOnly:
            urlparams += '"reduceOnly": "true",'
            if not (reason=='close'):
                urlparams += '"triggerPrice": "'+str(price)+'",'
                urlparams += '"triggerDirection": "'+str(triggerDirection)+'",'

        urlparams += '"qty": "'+str(quantity)+'",'
        
        urlparams += '"orderLinkId": "'+str(orderLinkId)+'"'
        urlparams += "}"

        response = self.HTTP_Request(self.order_create_endpoint,'POST',urlparams,"Create")
        response = json.loads(response)
        
        return (response)
    
    def CancelAllOrder(
            self,
            symbol
    ):
        urlparams = "{"
        urlparams += '"category":"linear",'
        urlparams += '"symbol" : "'+symbol+'"'
        urlparams += "}"

        response = self.HTTP_Request(self.order_cancel_all_endpoint, 'POST', urlparams, 'cancel')
        return (response)