import React, { createContext, useContext, useState, useEffect } from 'react';

// ═══════════════════════════════════════════════════════════════════════
// TRANSLATIONS - All UI text for the entire app
// ═══════════════════════════════════════════════════════════════════════
const translations = {
    en: {
        brand: { name: 'Louis AS Grid', short: 'LAS', tagline: 'Quantitative Trading System' },
        nav: {
            dashboard: 'Dashboard',
            deploy: 'Deploy',
            settings: 'Settings',
            admin: 'Admin',
            login: 'Login',
            register: 'Get Started',
            logout: 'Logout',
            back: '← Back'
        },
        common: {
            loading: 'Loading...',
            save: 'Save',
            cancel: 'Cancel',
            delete: 'Delete',
            edit: 'Edit',
            create: 'Create',
            submit: 'Submit',
            confirm: 'Confirm',
            success: 'Success',
            error: 'Error',
            saving: 'Saving...',
            testing: 'Testing...',
            saved: 'Saved',
            noData: 'No data'
        },
        landing: {
            tag: 'Automated Grid Trading',
            title1: 'Trade Smarter',
            title2: 'with Louis AS Grid',
            subtitle: 'Professional-grade grid trading bot for Bitget. Deploy your own node and start earning passive income 24/7.',
            cta: 'Start Trading',
            bitgetCta: 'No Bitget account?',
            bitgetLink: 'Register with bonus',
            referralNotice: 'Important: You must register Bitget using our referral link above.',
            referralNotice2: 'Only UIDs registered through our referral link can apply for free access!'
        },
        features: {
            title: 'Why Louis AS Grid?',
            list: [
                { title: 'Fully Automated', desc: 'Set and forget. Your bot trades 24/7.' },
                { title: 'Self-Hosted', desc: 'Your keys, your control. Deploy on Zeabur.' },
                { title: 'Grid Strategy', desc: 'Profit from market volatility.' },
                { title: 'One-Click Deploy', desc: 'Deploy in seconds with cloud.' }
            ]
        },
        steps: {
            title: 'Get Started',
            list: [
                { title: 'Register & Verify', desc: 'Connect Bitget API key' },
                { title: 'Deploy Node', desc: 'One-click cloud deploy' },
                { title: 'Start Trading', desc: 'Configure and launch' }
            ]
        },
        cta: {
            title: 'Ready to Trade?',
            button: 'Get Started Free',
            bitgetNote: 'New to Bitget?',
            bitgetLink: 'Register for bonus'
        },
        auth: {
            createAccount: 'Create Account',
            signIn: 'Sign In',
            email: 'Email Address',
            password: 'Password',
            confirmPassword: 'Confirm Password',
            forgotPassword: 'Forgot password?',
            noAccount: "Don't have an account?",
            hasAccount: 'Already have an account?',
            signUp: 'Sign up',
            loginBtn: 'Sign In',
            registerBtn: 'Create Account',
            passwordMin: 'Minimum 8 characters',
            passwordRequirements: 'Must contain: 8+ chars, 1 uppercase, 1 number',
            passwordUppercase: 'Include at least one uppercase letter',
            passwordNumber: 'Include at least one number',
            passwordsDoNotMatch: 'Passwords do not match',
            joinMessage: 'Join the quantitative trading revolution'
        },
        dashboard: {
            title: 'Dashboard',
            tradingNode: 'Trading Node',
            connected: 'Connected',
            notConfigured: 'Not Configured',
            error: 'Connection Error',
            checking: 'Checking...',
            lastUpdate: 'Last update',
            deployNode: 'Deploy Node',
            connectExisting: 'Connect Existing',
            startTrading: 'Start Trading',
            stopTrading: 'Stop Trading',
            retry: 'Retry',
            checkSettings: 'Check Settings',
            status: 'Status',
            running: 'Running',
            stopped: 'Stopped',
            pnl: 'PnL',
            buyOrders: 'Buy Orders',
            sellOrders: 'Sell Orders',
            tradingConfig: 'Trading Config',
            nodeInfo: 'Node Info',
            symbol: 'Symbol',
            gridCount: 'Grid Count',
            priceRange: 'Price Range',
            qtyPerGrid: 'Qty per Grid',
            nodeUrl: 'Node URL',
            uid: 'UID',
            connectionStatus: 'Connection',
            stable: 'Stable',
            getStarted: 'Get Started with Louis AS Grid',
            getStartedDesc: 'Deploy your personal trading node to start using quantitative grid trading.',
            deployYourNode: 'Deploy Your Node',
            nodeStatus: 'Node Status',
            nodeOffline: 'Node Offline',
            controlPanel: 'Control Panel',
            processing: 'Processing...',
            paused: 'Paused',
            pauseRefill: 'Pause Refill',
            resumeRefill: 'Resume Refill',
            closeAll: 'Close All Positions',
            positions: 'Positions',
            pair: 'Pair',
            long: 'Long',
            short: 'Short',
            unrealizedPnl: 'Unrealized PnL',
            indicators: 'Trading Indicators',
            totalPositions: 'Total Positions',
            tradingLog: 'Trading Log',
            realtime: 'Real-time',
            connecting: 'Connecting...',
            waitingForLogs: 'Waiting for trading logs...',
            equity: 'Equity',
            available: 'Available',
            totalPnl: 'Total PnL',
            floatingPnl: 'Floating PnL',
            futuresAccount: 'Futures Account',
            totalEquity: 'Total Equity',
            totalAvailable: 'Total Available',
            coins: 'Coins',
            backtest: 'Backtest'
        },
        deploy: {
            title: 'Deploy Node',
            heroTitle: 'Deploy Your Trading Node',
            heroSubtitle: 'Just one click to deploy your personal trading node',
            step1Title: 'One-Click Deploy',
            step1Desc: 'Click the button',
            step2Title: 'Confirm Deploy',
            step2Desc: 'Confirm in Zeabur',
            step3Title: 'Connect Node',
            step3Desc: 'Paste URL to settings',
            oneClickTitle: 'Deploy Your Trading Node',
            oneClickDesc: 'No technical background needed. One click to complete deployment.',
            oneClickBtn: 'Deploy to Zeabur',
            yourUserId: 'Your User ID (auto-filled)',
            yourBitgetUid: 'Your Bitget UID',
            securityNote: 'Secure encryption · No API keys required',
            afterDeployTitle: 'After Deployment',
            afterStep1: 'Wait for Zeabur deployment (~1-2 min)',
            afterStep2: 'Copy the generated domain from Zeabur',
            afterStep3: 'Return to Settings page, paste and save',
            goToSettings: 'Go to Settings',
            showAdvanced: 'Advanced: Manual Deploy',
            hideAdvanced: 'Hide Advanced Options',
            advancedTitle: 'Manual Deploy (Advanced)',
            advancedDesc: 'If you want to manage the code yourself:',
            envVars: 'Environment Variables',
            autoGenerated: '(auto-generated)',
            alreadyDeployed: 'Already deployed?',
            connectNode: 'Connect Your Node'
        },
        settings: {
            title: 'Node Settings',
            bindNode: 'Bind Trading Node',
            bindDesc: 'Connect your Zeabur deployed Grid trading node',
            nodeUrl: 'Node URL',
            nodeUrlPlaceholder: 'https://your-node.zeabur.app',
            nodeUrlHint: 'Copy from Zeabur Dashboard after deployment',
            nodeSecret: 'Node Secret',
            nodeSecretPlaceholder: 'Your NODE_SECRET',
            nodeSecretHint: 'NODE_SECRET environment variable set during deployment',
            testConnection: 'Test Connection',
            saveSettings: 'Save Settings',
            connectionSuccess: 'Connected! Node is running.',
            connectionFailed: 'Connection failed. Check URL and secret.',
            howToGet: 'How to get node URL?',
            instruction1: 'Go to Deploy page to complete one-click deployment',
            instruction2: 'Login to Zeabur Dashboard',
            instruction3: 'Find your grid-node service',
            instruction4: 'Click "Domains" to copy URL',
            instruction5: 'Paste in the field above and save'
        },
        admin: {
            title: 'Admin Panel',
            subtitle: 'Manage your Louis AS Grid system',
            overview: 'Overview',
            pending: 'Pending',
            users: 'Users',
            whitelist: 'Whitelist',
            groups: 'Groups',
            totalUsers: 'Total Users',
            pendingUsers: 'Pending',
            activeUsers: 'Active',
            totalGroups: 'Groups',
            cumulative: 'Cumulative',
            needsAction: 'Needs Action',
            running: 'Running',
            total: 'Total',
            pendingApproval: 'Pending Approval',
            viewAll: 'View All',
            manage: 'Manage',
            noPending: 'No pending users',
            noGroups: 'No groups yet',
            members: 'members',
            user: 'User',
            requestDate: 'Request Date',
            actions: 'Actions',
            approve: 'Approve',
            reject: 'Reject',
            group: 'Group',
            statusLabel: 'Status',
            active: 'Active',
            rejected: 'Rejected',
            pendingApprovalStatus: 'Pending Approval',
            pendingApi: 'Pending API',
            addUid: 'Add UID',
            newGroup: 'New Group',
            uidWhitelist: 'UID Whitelist',
            uidWhitelistDesc: 'Pre-approve Bitget UIDs. Matching users will be auto-approved.',
            approvedUsers: 'Approved Users',
            preApprovedUid: 'Pre-approved UIDs',
            noActiveUsers: 'No active users yet',
            noPreApproved: 'No pre-approved UIDs',
            addFirstUid: 'Add first UID',
            waiting: 'Waiting',
            enabled: 'Enabled',
            noDescription: 'No description',
            createFirstGroup: 'Create first group',
            addUidTitle: 'Add UID to Whitelist',
            bitgetUid: 'Bitget UID',
            emailOptional: 'Email (optional)',
            adding: 'Adding...',
            createGroupTitle: 'Create New Group',
            groupName: 'Group Name',
            groupDesc: 'Group Description',
            creating: 'Creating...',
            createGroup: 'Create Group',
            backToDashboard: 'Back to Dashboard',
            sysAdmin: 'System Admin',
            editUser: 'Edit User',
            noUsersFound: 'No users found',
            showingUsers: 'Showing',
            ofUsers: 'of',
            usersLabel: 'users',
            prev: 'Prev',
            next: 'Next',
            page: 'Page',
            addGroup: 'Add Group',
            assignGroup: 'Assign Group',
            noGroup: 'No Group'
        },
        footer: {
            rights: '© 2025 Louis AS Grid. All rights reserved.'
        },
        status: {
            active: 'Active',
            pending_approval: 'Pending Approval',
            pending_api: 'Pending API',
            rejected: 'Rejected'
        },
        setup: {
            title: 'Connect Bitget API',
            subtitle: 'Verify your identity to continue',
            step1: 'Instructions',
            step2: 'Enter API',
            howTo: 'How to get your Bitget API',
            instruction1: 'Log in to Bitget website',
            instruction2: 'Navigate to API Management',
            instruction3: 'Create a new API Key',
            instruction4: 'Enable "Read" permission (trading not required)',
            instruction5: 'Copy API Key, Secret, and Passphrase',
            openBitget: 'Open Bitget API Management',
            readyBtn: 'I have my API ready',
            apiKey: 'API Key',
            apiSecret: 'API Secret',
            passphrase: 'Passphrase',
            required: '*Required',
            back: 'Back',
            verify: 'Verify & Submit',
            verifying: 'Verifying...',
            securityNote: 'Your credentials are encrypted and securely stored for your trading node.'
        },
        rejected: {
            title: 'Access Denied',
            subtitle: 'Your account could not be verified',
            contact: 'If you believe this is an error, please contact our support team.',
            retry: 'Try Different Account',
            contactSupport: 'Contact Support'
        }
    },
    zh: {
        brand: { name: 'Louis AS Grid', short: 'LAS', tagline: '量化交易系統' },
        nav: {
            dashboard: '儀表板',
            deploy: '部署',
            settings: '設定',
            admin: '管理',
            login: '登入',
            register: '立即開始',
            logout: '登出',
            back: '← 返回'
        },
        common: {
            loading: '載入中...',
            save: '儲存',
            cancel: '取消',
            delete: '刪除',
            edit: '編輯',
            create: '建立',
            submit: '提交',
            confirm: '確認',
            success: '成功',
            error: '錯誤',
            saving: '儲存中...',
            testing: '測試中...',
            saved: '已儲存',
            noData: '無資料'
        },
        landing: {
            tag: '自動網格交易',
            title1: '聰明交易',
            title2: '選擇 Louis AS Grid',
            subtitle: '專業級 Bitget 網格交易機器人。部署專屬節點，24/7 自動賺取被動收入。',
            cta: '開始交易',
            bitgetCta: '還沒有 Bitget？',
            bitgetLink: '註冊享獎勵',
            referralNotice: '重要提醒：使用本系統前，請務必透過上方連結註冊 Bitget。',
            referralNotice2: '只有透過本站推薦連結註冊的 UID 才能免費使用！'
        },
        features: {
            title: '為什麼選擇 Louis AS Grid？',
            list: [
                { title: '全自動執行', desc: '設定即忘，24/7 不間斷交易。' },
                { title: '自主託管', desc: '密鑰自控，部署於 Zeabur。' },
                { title: '網格策略', desc: '從市場波動中獲利。' },
                { title: '一鍵部署', desc: '數秒內雲端部署。' }
            ]
        },
        steps: {
            title: '快速開始',
            list: [
                { title: '註冊驗證', desc: '連接 Bitget API' },
                { title: '部署節點', desc: '一鍵雲端部署' },
                { title: '開始交易', desc: '設定並啟動' }
            ]
        },
        cta: {
            title: '準備好了嗎？',
            button: '免費開始',
            bitgetNote: '新用戶？',
            bitgetLink: '註冊獲獎勵'
        },
        auth: {
            createAccount: '建立帳號',
            signIn: '登入',
            email: '電子郵件',
            password: '密碼',
            confirmPassword: '確認密碼',
            forgotPassword: '忘記密碼？',
            noAccount: '還沒有帳號？',
            hasAccount: '已有帳號？',
            signUp: '註冊',
            loginBtn: '登入',
            registerBtn: '建立帳號',
            passwordMin: '至少 8 個字元',
            passwordRequirements: '需包含：8+ 字元、1 大寫字母、1 數字',
            passwordUppercase: '需包含至少一個大寫字母',
            passwordNumber: '需包含至少一個數字',
            passwordsDoNotMatch: '密碼不相符',
            joinMessage: '加入量化交易革命'
        },
        dashboard: {
            title: '儀表板',
            tradingNode: '交易節點',
            connected: '已連線',
            notConfigured: '未設定',
            error: '連線失敗',
            checking: '檢查中...',
            lastUpdate: '最後更新',
            deployNode: '部署節點',
            connectExisting: '連接現有節點',
            startTrading: '開始交易',
            stopTrading: '停止交易',
            retry: '重試連線',
            checkSettings: '檢查設定',
            status: '運行狀態',
            running: '運行中',
            stopped: '已停止',
            pnl: '損益 (PnL)',
            buyOrders: '買入訂單',
            sellOrders: '賣出訂單',
            tradingConfig: '交易配置',
            nodeInfo: '節點資訊',
            symbol: '交易對',
            gridCount: '網格數量',
            priceRange: '價格範圍',
            qtyPerGrid: '每格數量',
            nodeUrl: '節點網址',
            uid: 'UID',
            connectionStatus: '連線狀態',
            stable: '穩定',
            getStarted: '開始使用 Louis AS Grid',
            getStartedDesc: '部署您的專屬交易節點，開始使用量化網格交易。',
            deployYourNode: '一鍵部署節點',
            nodeStatus: '節點狀態',
            nodeOffline: '節點離線',
            controlPanel: '控制台',
            processing: '處理中...',
            paused: '暫停中',
            pauseRefill: '暫停補倉',
            resumeRefill: '恢復補倉',
            closeAll: '一鍵平倉',
            positions: '持倉列表',
            pair: '交易對',
            long: '多頭',
            short: '空頭',
            unrealizedPnl: '浮盈',
            indicators: '交易指標',
            totalPositions: '總持倉',
            tradingLog: '交易日誌',
            realtime: '即時連線',
            connecting: '連線中...',
            waitingForLogs: '等待交易日誌...',
            equity: '權益',
            available: '可用',
            totalPnl: '總損益',
            floatingPnl: '浮動盈虧',
            futuresAccount: '合約帳戶',
            totalEquity: '總權益',
            totalAvailable: '總可用',
            coins: '選幣',
            backtest: '回測'
        },
        deploy: {
            title: '部署節點',
            heroTitle: '部署您的交易節點',
            heroSubtitle: '只需點擊一個按鈕，即可部署您的專屬交易節點',
            step1Title: '一鍵部署',
            step1Desc: '點擊按鈕開始',
            step2Title: '確認部署',
            step2Desc: '在 Zeabur 確認',
            step3Title: '連接節點',
            step3Desc: '貼上網域到設定',
            oneClickTitle: '一鍵部署您的交易節點',
            oneClickDesc: '無需任何技術背景，點擊按鈕即可完成部署',
            oneClickBtn: '一鍵部署到 Zeabur',
            yourUserId: '您的用戶 ID（已自動填入）',
            yourBitgetUid: '您的 Bitget UID',
            securityNote: '安全加密・無需提供 API 密鑰',
            afterDeployTitle: '部署完成後',
            afterStep1: '等待 Zeabur 部署完成（約 1-2 分鐘）',
            afterStep2: '在 Zeabur 頁面複製生成的網域',
            afterStep3: '返回本站設定頁面，貼上網域並儲存',
            goToSettings: '前往設定頁面',
            showAdvanced: '進階用戶：手動部署',
            hideAdvanced: '隱藏進階選項',
            advancedTitle: '手動部署（進階用戶）',
            advancedDesc: '如果您想自行管理程式碼，可以使用以下方式：',
            envVars: '環境變數',
            autoGenerated: '（自動生成）',
            alreadyDeployed: '已經部署好了？',
            connectNode: '連接您的節點'
        },
        settings: {
            title: '節點設定',
            bindNode: '綁定交易節點',
            bindDesc: '連接您在 Zeabur 部署的 Grid 交易節點',
            nodeUrl: '節點網址',
            nodeUrlPlaceholder: 'https://your-node.zeabur.app',
            nodeUrlHint: '部署完成後從 Zeabur Dashboard 複製您的服務網址',
            nodeSecret: '節點密鑰',
            nodeSecretPlaceholder: '您設定的 NODE_SECRET',
            nodeSecretHint: '部署時設定的 NODE_SECRET 環境變數',
            testConnection: '測試連線',
            saveSettings: '儲存設定',
            connectionSuccess: '連線成功！節點運作正常。',
            connectionFailed: '連線失敗，請確認網址和密鑰是否正確。',
            howToGet: '如何取得節點網址？',
            instruction1: '前往部署頁面完成一鍵部署',
            instruction2: '登入 Zeabur Dashboard',
            instruction3: '找到您的 grid-node 服務',
            instruction4: '點擊「Domains」複製網址',
            instruction5: '貼上上方欄位並儲存'
        },
        admin: {
            title: '管理後台',
            subtitle: '管理您的 Louis AS Grid 系統',
            overview: '總覽',
            pending: '待審核',
            users: '用戶列表',
            whitelist: '白名單',
            groups: '群組管理',
            totalUsers: '總用戶數',
            pendingUsers: '待審核',
            activeUsers: '已啟用',
            totalGroups: '群組數',
            cumulative: '累計',
            needsAction: '需處理',
            running: '運行中',
            total: '合計',
            pendingApproval: '待審核用戶',
            viewAll: '查看全部',
            manage: '管理',
            noPending: '目前無待審核用戶',
            noGroups: '尚未建立群組',
            members: '位成員',
            user: '用戶',
            requestDate: '申請日期',
            actions: '操作',
            approve: '通過',
            reject: '拒絕',
            group: '群組',
            statusLabel: '狀態',
            active: '已啟用',
            rejected: '已拒絕',
            pendingApprovalStatus: '待審核',
            pendingApi: '待驗證',
            addUid: '新增 UID',
            newGroup: '新增群組',
            uidWhitelist: 'UID 白名單',
            uidWhitelistDesc: '預先核准 Bitget UID。符合 UID 的用戶註冊後將自動通過審核。',
            approvedUsers: '已核准用戶',
            preApprovedUid: '預核准 UID',
            noActiveUsers: '尚無已啟用用戶',
            noPreApproved: '尚無預核准 UID',
            addFirstUid: '新增第一個 UID',
            waiting: '等待中',
            enabled: '已啟用',
            noDescription: '無描述',
            createFirstGroup: '建立第一個群組',
            addUidTitle: '新增 UID 至白名單',
            bitgetUid: 'Bitget UID',
            emailOptional: '電子郵件（選填）',
            adding: '新增中...',
            createGroupTitle: '建立新群組',
            groupName: '群組名稱',
            groupDesc: '群組描述',
            creating: '建立中...',
            createGroup: '建立群組',
            backToDashboard: '返回儀表板',
            sysAdmin: '系統管理員',
            editUser: '編輯用戶',
            noUsersFound: '找不到用戶',
            showingUsers: '顯示',
            ofUsers: '，共',
            usersLabel: '位用戶',
            prev: '上一頁',
            next: '下一頁',
            page: '第',
            addGroup: '新增群組',
            assignGroup: '指定群組',
            noGroup: '無群組'
        },
        footer: {
            rights: '© 2025 Louis AS Grid. All rights reserved.'
        },
        status: {
            active: '已啟用',
            pending_approval: '待審核',
            pending_api: '待驗證',
            rejected: '已拒絕'
        },
        setup: {
            title: '連接 Bitget API',
            subtitle: '驗證您的身分以繼續',
            step1: '操作說明',
            step2: '輸入 API',
            howTo: '如何取得 Bitget API？',
            instruction1: '登入 Bitget 網頁版',
            instruction2: '前往 API 管理頁面',
            instruction3: '建立新的 API Key',
            instruction4: '開啟「讀取」權限（無需交易權限）',
            instruction5: '複製 API Key、Secret 和 Passphrase',
            openBitget: '開啟 Bitget API 管理',
            readyBtn: '我已準備好 API',
            apiKey: 'API Key',
            apiSecret: 'API Secret',
            passphrase: 'Passphrase',
            required: '*必填',
            back: '上一步',
            verify: '驗證並提交',
            verifying: '驗證中...',
            securityNote: '您的憑證將加密儲存，供交易節點安全使用。'
        },
        rejected: {
            title: '存取被拒絕',
            subtitle: '您的帳號無法通過驗證',
            contact: '如果您認為這是錯誤，請聯繫客服團隊。',
            retry: '嘗試其他帳號',
            contactSupport: '聯繫客服'
        }
    }
};

// ═══════════════════════════════════════════════════════════════════════
// I18N CONTEXT
// ═══════════════════════════════════════════════════════════════════════
const I18nContext = createContext();

export const I18nProvider = ({ children }) => {
    const [lang, setLang] = useState(() => {
        return localStorage.getItem('language') || 'zh';
    });

    useEffect(() => {
        localStorage.setItem('language', lang);
    }, [lang]);

    const t = translations[lang];

    const toggleLang = () => {
        setLang(prev => prev === 'zh' ? 'en' : 'zh');
    };

    return (
        <I18nContext.Provider value={{ lang, setLang, toggleLang, t }}>
            {children}
        </I18nContext.Provider>
    );
};

export const useI18n = () => {
    const context = useContext(I18nContext);
    if (!context) {
        throw new Error('useI18n must be used within an I18nProvider');
    }
    return context;
};

// ═══════════════════════════════════════════════════════════════════════
// LANGUAGE TOGGLE COMPONENT
// ═══════════════════════════════════════════════════════════════════════
export const LanguageToggle = ({ className = '' }) => {
    const { lang, setLang } = useI18n();

    return (
        <div className={`flex items-center bg-white/5 border border-white/10 rounded-lg p-1 ${className}`}>
            <button
                onClick={() => setLang('en')}
                className={`px-3 py-1.5 text-[11px] font-medium rounded-md transition-all ${lang === 'en' ? 'bg-white text-black' : 'text-white/50 hover:text-white'}`}
            >
                EN
            </button>
            <button
                onClick={() => setLang('zh')}
                className={`px-3 py-1.5 text-[11px] font-medium rounded-md transition-all ${lang === 'zh' ? 'bg-white text-black' : 'text-white/50 hover:text-white'}`}
            >
                繁中
            </button>
        </div>
    );
};

// ═══════════════════════════════════════════════════════════════════════
// SHARED LOGO COMPONENT
// ═══════════════════════════════════════════════════════════════════════
export const Logo = ({ size = 'md', showText = true }) => {
    const { t } = useI18n();

    const sizes = {
        sm: { img: 'h-6', text: 'text-[10px]', name: 'text-[13px]' },
        md: { img: 'h-8', text: 'text-lg', name: 'text-xl' },
        lg: { img: 'h-12', text: 'text-2xl', name: 'text-3xl' }
    };

    const s = sizes[size];

    return (
        <div className="flex items-center gap-3">
            <img src="/logo.png" alt="Louis AS Grid" className={`${s.img} w-auto object-contain`} />
            {showText && (
                <div>
                    <span className={`font-semibold tracking-tight text-white ${s.name}`}>{t.brand.name}</span>
                </div>
            )}
        </div>
    );
};

export default translations;
