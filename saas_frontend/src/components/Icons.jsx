import React from 'react';

export const Icon = ({ path, className = "w-5 h-5", ...props }) => (
    <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={className}
        {...props}
    >
        {path}
    </svg>
);

export const Icons = {
    Rocket: (props) => (
        <Icon {...props} path={<><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z" /><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z" /><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0" /><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5" /></>} />
    ),
    Settings: (props) => (
        <Icon {...props} path={<><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.09a2 2 0 0 1-1-1.74v-.47a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.39a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" /><circle cx="12" cy="12" r="3" /></>} />
    ),
    Server: (props) => (
        <Icon {...props} path={<><rect width="20" height="8" x="2" y="2" rx="2" ry="2" /><rect width="20" height="8" x="2" y="14" rx="2" ry="2" /><line x1="6" x2="6.01" y1="6" y2="6" /><line x1="6" x2="6.01" y1="18" y2="18" /></>} />
    ),
    TrendingUp: (props) => (
        <Icon {...props} path={<><polyline points="23 6 13.5 15.5 8.5 10.5 1 18" /><polyline points="17 6 23 6 23 12" /></>} />
    ),
    Zap: (props) => (
        <Icon {...props} path={<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />} />
    ),
    Users: (props) => (
        <Icon {...props} path={<><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></>} />
    ),
    Link: (props) => (
        <Icon {...props} path={<><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" /></>} />
    ),
    Check: (props) => (
        <Icon {...props} path={<polyline points="20 6 9 17 4 12" />} />
    ),
    CheckCircle: (props) => (
        <Icon {...props} path={<><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></>} />
    ),
    X: (props) => (
        <Icon {...props} path={<><line x1="18" x2="6" y1="6" y2="18" /><line x1="6" x2="18" y1="6" y2="18" /></>} />
    ),
    AlertCircle: (props) => (
        <Icon {...props} path={<><circle cx="12" cy="12" r="10" /><line x1="12" x2="12" y1="8" y2="12" /><line x1="12" x2="12.01" y1="16" y2="16" /></>} />
    ),
    LogOut: (props) => (
        <Icon {...props} path={<><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" x2="9" y1="12" y2="12" /></>} />
    ),
    ArrowRight: (props) => (
        <Icon {...props} path={<><line x1="5" x2="19" y1="12" y2="12" /><polyline points="12 5 19 12 12 19" /></>} />
    ),
    ArrowLeft: (props) => (
        <Icon {...props} path={<><line x1="19" x2="5" y1="12" y2="12" /><polyline points="12 19 5 12 12 5" /></>} />
    ),
    RefreshCw: (props) => (
        <Icon {...props} path={<><path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8" /><path d="M21 3v5h-5" /></>} />
    ),
    Play: (props) => (
        <Icon {...props} path={<polygon points="5 3 19 12 5 21 5 3" />} />
    ),
    Square: (props) => (
        <Icon {...props} path={<rect width="18" height="18" x="3" y="3" rx="2" ry="2" />} />
    ),
    List: (props) => (
        <Icon {...props} path={<><line x1="8" x2="21" y1="6" y2="6" /><line x1="8" x2="21" y1="12" y2="12" /><line x1="8" x2="21" y1="18" y2="18" /><line x1="3" x2="3.01" y1="6" y2="6" /><line x1="3" x2="3.01" y1="12" y2="12" /><line x1="3" x2="3.01" y1="18" y2="18" /></>} />
    ),
    Globe: (props) => (
        <Icon {...props} path={<><circle cx="12" cy="12" r="10" /><line x1="2" x2="22" y1="12" y2="12" /><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" /></>} />
    ),
    Shield: (props) => (
        <Icon {...props} path={<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />} />
    ),
    Clock: (props) => (
        <Icon {...props} path={<><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></>} />
    ),
    Tag: (props) => (
        <Icon {...props} path={<><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" /><line x1="7" x2="7.01" y1="7" y2="7" /></>} />
    ),
    BarChart2: (props) => (
        <Icon {...props} path={<><line x1="18" x2="18" y1="20" y2="10" /><line x1="12" x2="12" y1="20" y2="4" /><line x1="6" x2="6" y1="20" y2="14" /></>} />
    ),
    Edit: (props) => (
        <Icon {...props} path={<><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></>} />
    ),
    Trash: (props) => (
        <Icon {...props} path={<><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></>} />
    ),
    Key: (props) => (
        <Icon {...props} path={<><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0 3 3L22 7l-3-3m-3.5 3.5L19 4" /></>} />
    ),
    Plus: (props) => (
        <Icon {...props} path={<><line x1="12" x2="12" y1="5" y2="19" /><line x1="5" x2="19" y1="12" y2="12" /></>} />
    ),
    Pause: (props) => (
        <Icon {...props} path={<><rect width="4" height="16" x="6" y="4" /><rect width="4" height="16" x="14" y="4" /></>} />
    ),
    Search: (props) => (
        <Icon {...props} path={<><circle cx="11" cy="11" r="8" /><line x1="21" x2="16.65" y1="21" y2="16.65" /></>} />
    ),
    Terminal: (props) => (
        <Icon {...props} path={<><polyline points="4 17 10 11 4 5" /><line x1="12" x2="20" y1="19" y2="19" /></>} />
    ),
};
