
# Standard library imports
import socket
import ssl
import select

# Local imports
from smartt_simple_protocol import SmarttSimpleProtocol


class SmarttClientException(BaseException):
    pass


##############################################################################
### SmarttClient class - encapsulates connection and communication with Smartt
### server, preseting a nice and easy to use API to the user
class SmarttClient(object):

    ##########################################################################

    #############
    # API Enums #
    #############
    marketNames = [
        "Bovespa",
        "BMF"
    ]

    orderStatuses = [
        "canceled",
        "executed",
        "hung",
        "hung_cancellable",
        "hung_pending",
        "partially_canceled",
        "partially_executed",
        "partially_executed_cancellable",
        "rejected",
        "expired"
    ]

    ordersEventsTypes = [
        "order_sent",
        "order_canceled",
        "order_changed",
        "order_executed",
        "order_expired"
    ]

    stopOrderStatuses = [
        "canceled_by_client",
        "canceled_expired_option",
        "canceled_not_allowed_market",
        "canceled_not_enough_balance",
        "canceled_not_positioned",
        "canceled_order_limit_exceeded",
        "hung",
        "sent",
        "expired"
    ]

    stopOrdersEventsTypes = [
        "stop_order_sent",
        "stop_order_canceled",
        "stop_order_triggered",
        "stop_order_expired"
    ]

    validityTypes = [
        "HJ",
        "DE",
        "AC"
    ]
    ##########################################################################

    ### Init function - connects to the server (possibly initializing the SSL
    ### protocol as well) and setups the protocol handler
    def __init__(self, host="smartt.s10i.com.br", port=5060, use_ssl=True,
                 print_raw_messages=False):
        self.host = host
        self.port = port
        self.smartt_socket = socket.create_connection((self.host, self.port))
        if use_ssl:
            self.smartt_socket = ssl.wrap_socket(self.smartt_socket)

        self.protocol = SmarttSimpleProtocol(self.smartt_socket.recv,
                                             self.smartt_socket.send,
                                             print_raw_messages)

    # Generic Wrapper for all Smartt functions - sends the function message
    # and returns the response (next message from the server)
    def smarttFunction(self, message):
        self.protocol.send(message)
        response = self.protocol.receive()

        if len(response) > 0 and response[0] == "ERROR":
            if len(response) != 2:
                print "STRANGE! Error response doesn't have 2 values: %s" % \
                      str(response)
            raise SmarttClientException(response[0] + ": " + response[1])

        return response

    ##########################################################################
    ### Generic messages (list of strings) handling ###
    ###################################################
    def sendMessage(self, message):
        self.protocol.send(message)

    def receiveMessage(self):
        return self.protocol.receive()
    ##########################################################################

    ##########################################################################
    ### Raw messages handling ###
    #############################
    def sendRawMessage(self, message):
        self.smartt_socket.send(message)

    # Reads everything available until timing out
    def receiveRawMessage(self):
        # Read in chunks of at most 4K - the magical number for recv calls :)
        receive_size = 4096
        # Timeout of half a second - just enough so that a continuous
        # transmission from the server isn't missed (totally arbitrary choice)
        select_timeout = 0.5

        # Has to receive something, so just use the blocking function
        data = self.smartt_socket.recv(receive_size)

        # Wait and check for data, if available, read, if times out, stops
        while len(select.select([self.smartt_socket], [], [],
                                select_timeout)[0]) > 0:
            data += self.smartt_socket.recv(receive_size)

        return data
    ##########################################################################

    ##########################################################################
    ### Helper functions ###
    ########################
    def checkAttributes(self, attributes, possibleValues):
        for attribute in attributes:
            if attribute not in possibleValues:
                raise SmarttClientException("Invalid attribute: " + attribute)


    def formatAttributes(self, name, attributes, possibleValues):
        if not attributes:
            return ""

        self.checkAttributes(attributes, possibleValues)

        return self.formatString(name, ",".join(attributes))

    def formatString(self, name, value, optional=True):
        if value is None:
            if not optional:
                raise SmarttClientException("Non-optional parameter is NULL: "
                                            + name)
            else:
                return []

        return [("%s=%s" % (name, value))]

    def formatInteger(self, name, value, optional=True):
        formattedValue = (str(int(value))
                          if value is not None else None)
        return self.formatString(name, formattedValue, optional)

    def formatDecimal2(self, name, value, optional=True):
        formattedValue = (("%.2f" % float(value))
                          if value is not None else None)
        return self.formatString(name, formattedValue, optional)

    def formatDecimal6(self, name, value, optional=True):
        formattedValue = (("%.6f" % float(value))
                          if value is not None else None)
        return self.formatString(name, formattedValue, optional)

    def formatDatetime(self, name, value, optional=True):
        formattedValue = (value.strftime("%Y-%m-%d %H:%M:%S")
                          if value is not None else None)
        return self.formatString(name, formattedValue, optional)

    def formatDate(self, name, value, optional=True):
        formattedValue = (value.strftime("%Y-%m-%d")
                          if value is not None else None)
        return self.formatString(name, formattedValue, optional)

    def formatBoolean(self, name, value, falseAndTrueValues=["no", "yes"], optional=True):
        formattedValue = None
        if value == 0 or value is False or value == falseAndTrueValues[0]:
            formattedValue = "0"
        elif value == 1 or value is True or value == falseAndTrueValues[1]:
            formattedValue = "1"
        else:
            raise SmarttClientException("Invalid boolean value '" + name +
                                        "': " + value)

        return self.formatString(name, formattedValue, optional)

    def formatEnum(self, name, value, enumValues, optional=True):
        if value is not None and value not in enumValues:
            raise SmarttClientException("Invalid '" + name +
                                        "' parameter value: " + value)

        return self.formatString(name, value, optional)

    def formatDictResponse(self, values, attributes, defaultAttributes=[]):
        if len(attributes) == 0:
            attributes = defaultAttributes

        return dict(zip(attributes, values))

    def formatListOfDictsResponse(self, values, attributes, defaultAttributes):
        if not attributes:
            attributes = defaultAttributes

        k = len(attributes)
        return [self.formatDictResponse(values[i:i + k], attributes) for i in
                xrange(0, len(values), k)]

    ##########################################################################
    ### Smartt functions ###
    ########################


    loginAttributes = [
        "message"]


    def login(self, s10iLogin = None, s10iPassword = None):
        message = ["login"]
        message += self.formatString("s10i_login", s10iLogin, optional=False)
        message += self.formatString("s10i_password", s10iPassword, optional=False)
        response = self.smarttFunction(filter(None, message))
        return unicode(response[0])

    logoutAttributes = [
        "message"]


    def logout(self):
        message = ["logout"]
        response = self.smarttFunction(filter(None, message))
        return unicode(response[0])

    loggedAttributes = [
        "message"]


    def logged(self):
        message = ["logged"]
        response = self.smarttFunction(filter(None, message))
        return unicode(response[0])

    getClientAttributes = [
        "natural_person_or_legal_person",
        "name_or_corporate_name",
        "gender",
        "document",
        "email",
        "s10i_login",
        "address",
        "number",
        "complement",
        "neighborhood",
        "postal_code",
        "city",
        "state",
        "country",
        "birthday",
        "main_phone",
        "secondary_phone",
        "company"]


    def getClient(self, returnAttributes = None):
        message = ["get_client"]
        message += self.formatAttributes("return_attributes", returnAttributes, self.getClientAttributes)
        response = self.smarttFunction(filter(None, message))
        return self.formatDictResponse(response, returnAttributes, self.getClientAttributes)

    updateClientAttributes = [
        "message"]


    def updateClient(self, s10iPassword = None, naturalPersonOrLegalPerson = None, nameOrCorporateName = None, gender = None, document = None, email = None, s10iLogin = None, newS10iPassword = None, address = None, number = None, complement = None, neighborhood = None, postalCode = None, city = None, state = None, country = None, birthday = None, mainPhone = None, secondaryPhone = None, company = None):
        message = ["update_client"]
        message += self.formatString("s10i_password", s10iPassword, optional=True)
        message += self.formatBoolean("natural_person_or_legal_person", naturalPersonOrLegalPerson, optional=True)
        message += self.formatString("name_or_corporate_name", nameOrCorporateName, optional=True)
        message += self.formatChar("gender", gender, optional=True)
        message += self.formatInteger("document", document, optional=False)
        message += self.formatString("email", email, optional=False)
        message += self.formatString("s10i_login", s10iLogin, optional=False)
        message += self.formatString("new_s10i_password", newS10iPassword, optional=True)
        message += self.formatString("address", address, optional=True)
        message += self.formatString("number", number, optional=True)
        message += self.formatString("complement", complement, optional=True)
        message += self.formatString("neighborhood", neighborhood, optional=True)
        message += self.formatString("postal_code", postalCode, optional=True)
        message += self.formatString("city", city, optional=True)
        message += self.formatString("state", state, optional=True)
        message += self.formatString("country", country, optional=True)
        message += self.formatDate("birthday", birthday, optional=True)
        message += self.formatString("main_phone", mainPhone, optional=True)
        message += self.formatString("secondary_phone", secondaryPhone, optional=True)
        message += self.formatString("company", company, optional=True)
        response = self.smarttFunction(filter(None, message))
        return unicode(response[0])

    getClientBrokeragesAttributes = [
        "brokerage_id",
        "brokerage_login"]


    def getClientBrokerages(self, brokerageId = None, brokerageLogin = None, returnAttributes = None):
        message = ["get_client_brokerages"]
        message += self.formatInteger("brokerage_id", brokerageId, optional=True)
        message += self.formatString("brokerage_login", brokerageLogin, optional=True)
        message += self.formatAttributes("return_attributes", returnAttributes, self.getClientBrokeragesAttributes)
        response = self.smarttFunction(filter(None, message))
        return self.formatDictResponse(response, returnAttributes, self.getClientBrokeragesAttributes)

    insertClientBrokerageAttributes = [
        "message"]


    def insertClientBrokerage(self, brokerageId = None, brokerageLogin = None, brokeragePassword = None, brokerageDigitalSignature = None):
        message = ["insert_client_brokerage"]
        message += self.formatInteger("brokerage_id", brokerageId, optional=False)
        message += self.formatString("brokerage_login", brokerageLogin, optional=False)
        message += self.formatString("brokerage_password", brokeragePassword, optional=False)
        message += self.formatString("brokerage_digital_signature", brokerageDigitalSignature, optional=False)
        response = self.smarttFunction(filter(None, message))
        return unicode(response[0])

    updateClientBrokerageAttributes = [
        "message"]


    def updateClientBrokerage(self, brokerageId = None, newBrokerageId = None, brokerageLogin = None, brokeragePassword = None, brokerageDigiralSignature = None):
        message = ["update_client_brokerage"]
        message += self.formatInteger("brokerage_id", brokerageId, optional=False)
        message += self.formatInteger("new_brokerage_id", newBrokerageId, optional=True)
        message += self.formatString("brokerage_login", brokerageLogin, optional=True)
        message += self.formatString("brokerage_password", brokeragePassword, optional=True)
        message += self.formatString("brokerage_digiral_signature", brokerageDigiralSignature, optional=True)
        response = self.smarttFunction(filter(None, message))
        return unicode(response[0])

    deleteClientBrokeragesAttributes = [
        "message"]


    def deleteClientBrokerages(self, brokerageId = None, brokerageLogin = None):
        message = ["delete_client_brokerages"]
        message += self.formatInteger("brokerage_id", brokerageId, optional=True)
        message += self.formatString("brokerage_login", brokerageLogin, optional=True)
        response = self.smarttFunction(filter(None, message))
        return unicode(response[0])

    getStockAttributes = [
        "stock_code",
        "market_name",
        "company_name",
        "kind_of_stock",
        "isin_code",
        "trading_lot_size",
        "kind_of_quotation",
        "type",
        "code_underlying_stock",
        "exercise_price",
        "expiration_date"]


    def getStock(self, stockCode = None, marketName = None, returnAttributes = None):
        message = ["get_stock"]
        message += self.formatString("stock_code", stockCode, optional=False)
        message += self.formatString("market_name", marketName, optional=True)
        message += self.formatAttributes("return_attributes", returnAttributes, self.getStockAttributes)
        response = self.smarttFunction(filter(None, message))
        return self.formatDictResponse(response, returnAttributes, self.getStockAttributes)

    sendOrderAttributes = [
        "order_id"]


    def sendOrder(self, investmentCode = None, brokerageId = None, orderType = None, stockCode = None, marketName = None, numberOfStocks = None, price = None, validityType = None, validity = None):
        message = ["send_order"]
        message += self.formatString("investment_code", investmentCode, optional=False)
        message += self.formatInteger("brokerage_id", brokerageId, optional=True)
        message += self.formatBoolean("order_type", orderType, optional=False)
        message += self.formatString("stock_code", stockCode, optional=False)
        message += self.formatString("market_name", marketName, optional=True)
        message += self.formatInteger("number_of_stocks", numberOfStocks, optional=False)
        message += self.formatDecimal2("price", price, optional=False)
        message += self.formatString("validity_type", validityType, optional=True)
        message += self.formatDate("validity", validity, optional=True)
        response = self.smarttFunction(filter(None, message))
        return int(response[1])

    cancelOrderAttributes = [
        "order_id"]


    def cancelOrder(self, orderId = None):
        message = ["cancel_order"]
        message += self.formatInteger("order_id", orderId, optional=False)
        response = self.smarttFunction(filter(None, message))
        return int(response[1])

    changeOrderAttributes = [
        "order_id"]


    def changeOrder(self, orderId = None, newNumberOfStocks = None, newPrice = None):
        message = ["change_order"]
        message += self.formatInteger("order_id", orderId, optional=False)
        message += self.formatInteger("new_number_of_stocks", newNumberOfStocks, optional=True)
        message += self.formatDecimal2("new_price", newPrice, optional=True)
        response = self.smarttFunction(filter(None, message))
        return int(response[1])

    getOrdersAttributes = [
        "order_id",
        "order_id_in_brokerage",
        "investment_code",
        "brokerage_id",
        "is_real",
        "order_type",
        "stock_code",
        "market_name",
        "datetime",
        "number_of_stocks",
        "price",
        "financial_volume",
        "validity_type",
        "validity",
        "number_of_traded_stocks",
        "average_nominal_price",
        "status",
        "absolute_brokerage_tax_cost",
        "percentual_brokerage_tax_cost",
        "iss_tax_cost"]


    def getOrders(self, orderId = None, investmentCode = None, brokerageId = None, initialDatetime = None, finalDatetime = None, status = None, returnAttributes = None):
        message = ["get_orders"]
        message += self.formatInteger("order_id", orderId, optional=True)
        message += self.formatString("investment_code", investmentCode, optional=True)
        message += self.formatInteger("brokerage_id", brokerageId, optional=True)
        message += self.formatDatetime("initial_datetime", initialDatetime, optional=True)
        message += self.formatDatetime("final_datetime", finalDatetime, optional=True)
        message += self.formatString("status", status, optional=True)
        message += self.formatAttributes("return_attributes", returnAttributes, self.getOrdersAttributes)
        response = self.smarttFunction(filter(None, message))
        return self.formatListOfDictsResponse(response, returnAttributes, self.getOrdersAttributes)

    getOrdersEventsAttributes = [
        "order_id",
        "investment_code",
        "brokerage_id",
        "number_of_events",
        "datetime",
        "event_type",
        "description"]


    def getOrdersEvents(self, orderId = None, investmentCode = None, brokerageId = None, initialDatetime = None, finalDatetime = None, eventType = None, returnAttributes = None):
        message = ["get_orders_events"]
        message += self.formatInteger("order_id", orderId, optional=True)
        message += self.formatString("investment_code", investmentCode, optional=True)
        message += self.formatInteger("brokerage_id", brokerageId, optional=True)
        message += self.formatDatetime("initial_datetime", initialDatetime, optional=True)
        message += self.formatDatetime("final_datetime", finalDatetime, optional=True)
        message += self.formatString("event_type", eventType, optional=True)
        message += self.formatAttributes("return_attributes", returnAttributes, self.getOrdersEventsAttributes)
        response = self.smarttFunction(filter(None, message))
        return self.formatListOfDictsResponse(response, returnAttributes, self.getOrdersEventsAttributes)

    getOrderIdAttributes = [
        "order_id"]


    def getOrderId(self, orderIdInBrokerage = None, brokerageId = None):
        message = ["get_order_id"]
        message += self.formatString("order_id_in_brokerage", orderIdInBrokerage, optional=False)
        message += self.formatInteger("brokerage_id", brokerageId, optional=False)
        response = self.smarttFunction(filter(None, message))
        return int(response[0])

    sendStopOrderAttributes = [
        "stop_order_id"]


    def sendStopOrder(self, investmentCode = None, brokerageId = None, orderType = None, stopOrderType = None, stockCode = None, marketName = None, numberOfStocks = None, stopPrice = None, limitPrice = None, validity = None, validAfterMarket = None):
        message = ["send_stop_order"]
        message += self.formatString("investment_code", investmentCode, optional=False)
        message += self.formatInteger("brokerage_id", brokerageId, optional=True)
        message += self.formatBoolean("order_type", orderType, optional=False)
        message += self.formatBoolean("stop_order_type", stopOrderType, optional=False)
        message += self.formatString("stock_code", stockCode, optional=False)
        message += self.formatString("market_name", marketName, optional=True)
        message += self.formatInteger("number_of_stocks", numberOfStocks, optional=False)
        message += self.formatDecimal2("stop_price", stopPrice, optional=False)
        message += self.formatDecimal2("limit_price", limitPrice, optional=False)
        message += self.formatDate("validity", validity, optional=False)
        message += self.formatBoolean("valid_after_market", validAfterMarket, optional=False)
        response = self.smarttFunction(filter(None, message))
        return int(response[1])

    cancelStopOrderAttributes = [
        "stop_order_id"]


    def cancelStopOrder(self, stopOrderId = None):
        message = ["cancel_stop_order"]
        message += self.formatInteger("stop_order_id", stopOrderId, optional=False)
        response = self.smarttFunction(filter(None, message))
        return int(response[1])

    getStopOrdersAttributes = [
        "stop_order_id",
        "order_id_in_brokerage",
        "investment_code",
        "brokerage_id",
        "is_real",
        "order_type",
        "stop_order_type",
        "stock_code",
        "market_name",
        "datetime",
        "number_of_stocks",
        "stop_price",
        "limit_price",
        "validity",
        "valid_after_market",
        "status",
        "sent_order_id"]


    def getStopOrders(self, stopOrderId = None, investmentCode = None, brokerageId = None, initialDatetime = None, finalDatetime = None, status = None, returnAttributes = None):
        message = ["get_stop_orders"]
        message += self.formatInteger("stop_order_id", stopOrderId, optional=True)
        message += self.formatString("investment_code", investmentCode, optional=True)
        message += self.formatInteger("brokerage_id", brokerageId, optional=True)
        message += self.formatDatetime("initial_datetime", initialDatetime, optional=True)
        message += self.formatDatetime("final_datetime", finalDatetime, optional=True)
        message += self.formatString("status", status, optional=True)
        message += self.formatAttributes("return_attributes", returnAttributes, self.getStopOrdersAttributes)
        response = self.smarttFunction(filter(None, message))
        return self.formatListOfDictsResponse(response, returnAttributes, self.getStopOrdersAttributes)

    getStopOrdersEventsAttributes = [
        "stop_order_id",
        "investment_code",
        "brokerage_id",
        "number_of_events",
        "datetime",
        "event_type",
        "description"]


    def getStopOrdersEvents(self, stopOrderId = None, investmentCode = None, brokerageId = None, initialDatetime = None, finalDatetime = None, eventType = None, returnAttributes = None):
        message = ["get_stop_orders_events"]
        message += self.formatInteger("stop_order_id", stopOrderId, optional=True)
        message += self.formatString("investment_code", investmentCode, optional=True)
        message += self.formatInteger("brokerage_id", brokerageId, optional=True)
        message += self.formatDatetime("initial_datetime", initialDatetime, optional=True)
        message += self.formatDatetime("final_datetime", finalDatetime, optional=True)
        message += self.formatString("event_type", eventType, optional=True)
        message += self.formatAttributes("return_attributes", returnAttributes, self.getStopOrdersEventsAttributes)
        response = self.smarttFunction(filter(None, message))
        return self.formatListOfDictsResponse(response, returnAttributes, self.getStopOrdersEventsAttributes)

    getStopOrderIdAttributes = [
        "stop_order_id"]


    def getStopOrderId(self, stopOrderIdInBrokerage = None, brokerageId = None):
        message = ["get_stop_order_id"]
        message += self.formatString("stop_order_id_in_brokerage", stopOrderIdInBrokerage, optional=False)
        message += self.formatInteger("brokerage_id", brokerageId, optional=False)
        response = self.smarttFunction(filter(None, message))
        return int(response[0])

    getTradesAttributes = [
        "order_id",
        "trade_id_in_brokerage",
        "investment_code",
        "brokerage_id",
        "is_real",
        "trade_type",
        "stock_code",
        "market_name",
        "datetime",
        "number_of_stocks",
        "price",
        "financial_volume",
        "trading_tax_cost",
        "liquidation_tax_cost",
        "register_tax_cost",
        "income_tax_cost",
        "withholding_income_tax_cost",
        "other_taxes_cost"]


    def getTrades(self, orderId = None, investmentCode = None, brokerageId = None, initialDatetime = None, finalDatetime = None, returnAttributes = None):
        message = ["get_trades"]
        message += self.formatInteger("order_id", orderId, optional=True)
        message += self.formatString("investment_code", investmentCode, optional=True)
        message += self.formatInteger("brokerage_id", brokerageId, optional=False)
        message += self.formatDatetime("initial_datetime", initialDatetime, optional=True)
        message += self.formatDatetime("final_datetime", finalDatetime, optional=True)
        message += self.formatAttributes("return_attributes", returnAttributes, self.getTradesAttributes)
        response = self.smarttFunction(filter(None, message))
        return self.formatListOfDictsResponse(response, returnAttributes, self.getTradesAttributes)

    getInvestmentsAttributes = [
        "name",
        "code",
        "brokerage_id",
        "setup_code",
        "is_real",
        "initial_datetime",
        "final_datetime"]


    def getInvestments(self, investmentCode = None, brokerageId = None, returnAttributes = None):
        message = ["get_investments"]
        message += self.formatString("investment_code", investmentCode, optional=True)
        message += self.formatInteger("brokerage_id", brokerageId, optional=True)
        message += self.formatAttributes("return_attributes", returnAttributes, self.getInvestmentsAttributes)
        response = self.smarttFunction(filter(None, message))
        return self.formatDictResponse(response, returnAttributes, self.getInvestmentsAttributes)

    getReportAttributes = [
        "investment_code",
        "brokerage_id",
        "setup_code",
        "initial_datetime",
        "final_datetime",
        "number_of_days",
        "total_contributions",
        "total_withdraws",
        "initial_capital",
        "balance",
        "equity",
        "taxes_and_operational_costs",
        "gross_return",
        "gross_daily_return",
        "gross_annualized_return",
        "net_return",
        "net_daily_return",
        "net_annualized_return",
        "absolute_initial_drawdown",
        "percentual_initial_drawdown",
        "absolute_maximum_drawdown",
        "percentual_maximum_drawdown",
        "gross_profit",
        "gross_loss",
        "total_gross_profit",
        "net_profit",
        "net_loss",
        "total_net_profit",
        "profit_factor",
        "number_of_eliminations",
        "expected_payoff",
        "absolute_number_of_profit_eliminations",
        "percentual_number_of_profit_eliminations",
        "absolute_largest_profit_elimination",
        "percentual_largest__profit_elimination",
        "average_profit_in_profit_eliminations",
        "maximum_consecutive_profit_eliminations",
        "total_profit_in_maximum_consecutive_profit_eliminatons",
        "absolute_number_of_loss_eliminations",
        "percentual_number_of_loss_eliminations",
        "absolute_largest_loss_elimination",
        "percentual_largest__loss_elimination",
        "average_loss_in_loss_eliminations",
        "maximum_consecutive_loss_eliminations",
        "total_loss_in_maximum_consecutive_loss_eliminations",
        "absolute_number_of_eliminations_of_long_positions",
        "percentual_number_of_eliminations_of_long_positions",
        "absolute_number_of_profit_eliminations_of_long_positions",
        "percentual_number_of_profit_eliminations_of_long_positions",
        "absolute_number_of_loss_eliminations_of_long_positions",
        "percentual_number_of_loss_eliminations_of_long_positions",
        "absolute_number_of_eliminations_of_short_positions",
        "percentual_number_of_eliminations_of_short_positions",
        "absolute_number_of_profit_eliminations_of_short_positions",
        "percentual_number_of_profit_eliminations_of_short_positions",
        "absolute_number_of_loss_eliminations_of_short_positions",
        "percentual_number_of_loss_eliminations_of_short_positions"]


    def getReport(self, investmentCode = None, brokerageId = None, returnAttributes = None):
        message = ["get_report"]
        message += self.formatString("investment_code", investmentCode, optional=False)
        message += self.formatInteger("brokerage_id", brokerageId, optional=True)
        message += self.formatAttributes("return_attributes", returnAttributes, self.getReportAttributes)
        response = self.smarttFunction(filter(None, message))
        return self.formatDictResponse(response, returnAttributes, self.getReportAttributes)

    getDailyCumulativePerformanceAttributes = [
        "investment_code",
        "brokerage_id",
        "daily_cumulative_performance"]


    def getDailyCumulativePerformance(self, investmentCode = None, brokerageId = None):
        message = ["get_daily_cumulative_performance"]
        message += self.formatString("investment_code", investmentCode, optional=False)
        message += self.formatInteger("brokerage_id", brokerageId, optional=True)
        response = self.smarttFunction(filter(None, message))
        return self.formatDictResponse(response, [], self.getDailyCumulativePerformanceAttributes)

    getDailyDrawdownAttributes = [
        "investment_code",
        "brokerage_id",
        "daily_drawdown"]


    def getDailyDrawdown(self, investmentCode = None, brokerageId = None):
        message = ["get_daily_drawdown"]
        message += self.formatString("investment_code", investmentCode, optional=False)
        message += self.formatInteger("brokerage_id", brokerageId, optional=True)
        response = self.smarttFunction(filter(None, message))
        return self.formatDictResponse(response, [], self.getDailyDrawdownAttributes)

    getPortfolioAttributes = [
        "investment_code",
        "brokerage_id",
        "stock_code",
        "position_type",
        "number_of_stocks",
        "average_price",
        "financial_volume"]


    def getPortfolio(self, investmentCode = None, brokerageId = None, returnAttributes = None):
        message = ["get_portfolio"]
        message += self.formatString("investment_code", investmentCode, optional=False)
        message += self.formatInteger("brokerage_id", brokerageId, optional=True)
        message += self.formatAttributes("return_attributes", returnAttributes, self.getPortfolioAttributes)
        response = self.smarttFunction(filter(None, message))
        return self.formatListOfDictsResponse(response, returnAttributes, self.getPortfolioAttributes)

    getAvailableLimitsAttributes = [
        "spot",
        "option",
        "margin"]


    def getAvailableLimits(self, investmentCode = None, brokerageId = None, returnAttributes = None):
        message = ["get_available_limits"]
        message += self.formatString("investment_code", investmentCode, optional=True)
        message += self.formatInteger("brokerage_id", brokerageId, optional=True)
        message += self.formatAttributes("return_attributes", returnAttributes, self.getAvailableLimitsAttributes)
        response = self.smarttFunction(filter(None, message))
        return self.formatListOfDictsResponse(response, returnAttributes, self.getAvailableLimitsAttributes)

    getSetupsAttributes = [
        "name",
        "code",
        "initial_capital",
        "slippage",
        "absolute_brokerage_tax",
        "percentual_brokerage_tax",
        "position_trading_tax",
        "position_liquidation_tax",
        "position_register_tax",
        "position_income_tax",
        "position_withholding_income_tax",
        "position_other_taxes",
        "day_trade_trading_tax",
        "day_trade_liquidation_tax",
        "day_trade_regiter_tax",
        "day_trade_income_tax",
        "day_trade_withholding_income_tax",
        "day_trade_other_taxes",
        "iss_tax",
        "custody_tax",
        "lease_tax",
        "income_tax_payment"]


    def getSetups(self, code = None, returnAttributes = None):
        message = ["get_setups"]
        message += self.formatString("code", code, optional=True)
        message += self.formatAttributes("return_attributes", returnAttributes, self.getSetupsAttributes)
        response = self.smarttFunction(filter(None, message))
        return self.formatDictResponse(response, returnAttributes, self.getSetupsAttributes)

    updateSetupAttributes = [
        "message"]


    def updateSetup(self, code = None, name = None, newCode = None, initialCapital = None, slippage = None, absoluteBrokerageTax = None, percentualBrokerageTax = None, positionTradingTax = None, positionLiquidationTax = None, positionRegisterTax = None, positionIncomeTax = None, positionWithholdingIncomeTax = None, positionOtherTaxes = None, dayTradeTradingTax = None, dayTradeLiquidationTax = None, dayTradeRegiterTax = None, dayTradeIncomeTax = None, dayTradeWithholdingIncomeTax = None, dayTradeOtherTaxes = None, issTax = None, custodyTax = None, leaseTax = None, incomeTaxPayment = None):
        message = ["update_setup"]
        message += self.formatString("code", code, optional=False)
        message += self.formatString("name", name, optional=True)
        message += self.formatString("new_code", newCode, optional=True)
        message += self.formatString("initial_capital", initialCapital, optional=True)
        message += self.formatDecimal2("slippage", slippage, optional=True)
        message += self.formatDecimal2("absolute_brokerage_tax", absoluteBrokerageTax, optional=True)
        message += self.formatDecimal2("percentual_brokerage_tax", percentualBrokerageTax, optional=True)
        message += self.formatDecimal2("position_trading_tax", positionTradingTax, optional=True)
        message += self.formatDecimal2("position_liquidation_tax", positionLiquidationTax, optional=True)
        message += self.formatDecimal2("position_register_tax", positionRegisterTax, optional=True)
        message += self.formatDecimal2("position_income_tax", positionIncomeTax, optional=True)
        message += self.formatDecimal2("position_withholding_income_tax", positionWithholdingIncomeTax, optional=True)
        message += self.formatDecimal2("position_other_taxes", positionOtherTaxes, optional=True)
        message += self.formatDecimal2("day_trade_trading_tax", dayTradeTradingTax, optional=True)
        message += self.formatDecimal2("day_trade_liquidation_tax", dayTradeLiquidationTax, optional=True)
        message += self.formatDecimal2("day_trade_regiter_tax", dayTradeRegiterTax, optional=True)
        message += self.formatDecimal2("day_trade_income_tax", dayTradeIncomeTax, optional=True)
        message += self.formatDecimal2("day_trade_withholding_income_tax", dayTradeWithholdingIncomeTax, optional=True)
        message += self.formatDecimal2("day_trade_other_taxes", dayTradeOtherTaxes, optional=True)
        message += self.formatDecimal2("iss_tax", issTax, optional=True)
        message += self.formatDecimal2("custody_tax", custodyTax, optional=True)
        message += self.formatDecimal2("lease_tax", leaseTax, optional=True)
        message += self.formatString("income_tax_payment", incomeTaxPayment, optional=True)
        response = self.smarttFunction(filter(None, message))
        return unicode(response[0])

    getFinancialTransactionsAttributes = [
        "financial_transaction_id",
        "investment_code",
        "brokerage_id",
        "datetime",
        "contribution_or_withdrawal",
        "value",
        "operational_tax_cost",
        "description"]


    def getFinancialTransactions(self, financialTransactionId = None, investmentCode = None, brokerageId = None, returnAttributes = None):
        message = ["get_financial_transactions"]
        message += self.formatString("financial_transaction_id", financialTransactionId, optional=True)
        message += self.formatString("investment_code", investmentCode, optional=True)
        message += self.formatInteger("brokerage_id", brokerageId, optional=True)
        message += self.formatAttributes("return_attributes", returnAttributes, self.getFinancialTransactionsAttributes)
        response = self.smarttFunction(filter(None, message))
        return self.formatDictResponse(response, returnAttributes, self.getFinancialTransactionsAttributes)

    insertFinancialTransactionAttributes = [
        "message"]


    def insertFinancialTransaction(self, investmentCode = None, brokerageId = None, datetime = None, contributionOrWithdrawal = None, value = None, operationalTaxCost = None, description = None):
        message = ["insert_financial_transaction"]
        message += self.formatString("investment_code", investmentCode, optional=False)
        message += self.formatInteger("brokerage_id", brokerageId, optional=True)
        message += self.formatDatetime("datetime", datetime, optional=False)
        message += self.formatBoolean("contribution_or_withdrawal", contributionOrWithdrawal, optional=False)
        message += self.formatDecimal2("value", value, optional=False)
        message += self.formatDecimal2("operational_tax_cost", operationalTaxCost, optional=False)
        message += self.formatString("description", description, optional=True)
        response = self.smarttFunction(filter(None, message))
        return unicode(response[0])

    updateFinancialTransactionAttributes = [
        "message"]


    def updateFinancialTransaction(self, financialTransactionId = None, investmentCode = None, brokerageId = None, datetime = None, contributionOrWithdrawal = None, value = None, operationalTaxCost = None, description = None):
        message = ["update_financial_transaction"]
        message += self.formatString("financial_transaction_id", financialTransactionId, optional=False)
        message += self.formatString("investment_code", investmentCode, optional=True)
        message += self.formatInteger("brokerage_id", brokerageId, optional=True)
        message += self.formatDatetime("datetime", datetime, optional=True)
        message += self.formatBoolean("contribution_or_withdrawal", contributionOrWithdrawal, optional=True)
        message += self.formatDecimal2("value", value, optional=True)
        message += self.formatDecimal2("operational_tax_cost", operationalTaxCost, optional=True)
        message += self.formatString("description", description, optional=True)
        response = self.smarttFunction(filter(None, message))
        return unicode(response[0])

    deleteFinancialTransactionsAttributes = [
        "message"]


    def deleteFinancialTransactions(self, financialTransactionId = None, investmentCode = None, brokerageId = None):
        message = ["delete_financial_transactions"]
        message += self.formatString("financial_transaction_id", financialTransactionId, optional=True)
        message += self.formatString("investment_code", investmentCode, optional=True)
        message += self.formatInteger("brokerage_id", brokerageId, optional=True)
        response = self.smarttFunction(filter(None, message))
        return unicode(response[0])

