'use strict';

const https = require('https');
const querystring = require('querystring');

// Import embedded configuration (Lambda@Edge doesn't support environment variables)
const CONFIG = require('./config.js');

// Configuration from embedded config file
const GITHUB_CLIENT_ID = CONFIG.GITHUB_CLIENT_ID;
const GITHUB_CLIENT_SECRET = CONFIG.GITHUB_CLIENT_SECRET;
const GITHUB_ORG = CONFIG.GITHUB_ORG;
const ALLOWED_TEAMS = CONFIG.ALLOWED_TEAMS;
const PUBLIC_PATHS = CONFIG.PUBLIC_PATHS;

// Cache for GitHub API responses (5 minute TTL)
const cache = new Map();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

exports.handler = async (event) => {
    const request = event.Records[0].cf.request;
    const headers = request.headers;
    const uri = request.uri;
    const querystring_params = request.querystring;

    console.log(`Processing request for: ${uri}`);

    // Handle OAuth callback
    if (uri === '/auth/callback') {
        console.log('Processing OAuth callback');
        return await handleOAuthCallback(querystring_params);
    }

    // Check if path is public
    if (isPublicPath(uri)) {
        console.log(`Public path: ${uri}`);
        return request;
    }

    // Check for authentication token
    const authToken = getAuthToken(headers);
    if (!authToken) {
        console.log('No auth token found');
        return generateAuthResponse(uri);
    }

    try {
        // Validate GitHub token and check team membership
        const isValid = await validateGitHubToken(authToken);
        if (isValid) {
            console.log('Valid authentication');
            return request;
        } else {
            console.log('Invalid authentication');
            return generateAuthResponse(uri);
        }
    } catch (error) {
        console.error('Authentication error:', error);
        return generateErrorResponse();
    }
};

function isPublicPath(uri) {
    return PUBLIC_PATHS.some(path => {
        if (path.endsWith('*')) {
            return uri.startsWith(path.slice(0, -1));
        }
        return uri === path;
    });
}

function getAuthToken(headers) {
    // Check cookie first
    if (headers.cookie) {
        const cookies = parseCookies(headers.cookie[0].value);
        if (cookies.github_token) {
            return cookies.github_token;
        }
    }

    // Check Authorization header
    if (headers.authorization) {
        const auth = headers.authorization[0].value;
        if (auth.startsWith('Bearer ')) {
            return auth.substring(7);
        }
    }

    return null;
}

function parseCookies(cookieString) {
    const cookies = {};
    cookieString.split(';').forEach(cookie => {
        const [name, value] = cookie.trim().split('=');
        if (name && value) {
            cookies[name] = value;
        }
    });
    return cookies;
}

async function validateGitHubToken(token) {
    // Check cache first
    const cacheKey = `token:${token}`;
    const cached = cache.get(cacheKey);
    if (cached && cached.expires > Date.now()) {
        console.log('Using cached validation result');
        return cached.valid;
    }

    // Validate token with GitHub API
    const user = await getGitHubUser(token);
    if (!user) {
        cache.set(cacheKey, { valid: false, expires: Date.now() + CACHE_TTL });
        return false;
    }

    // Check team membership
    const isMember = await checkTeamMembership(token, user.login);

    // Cache result
    cache.set(cacheKey, { valid: isMember, expires: Date.now() + CACHE_TTL });

    return isMember;
}

async function getGitHubUser(token) {
    return new Promise((resolve) => {
        const options = {
            hostname: 'api.github.com',
            path: '/user',
            method: 'GET',
            headers: {
                'Authorization': `token ${token}`,
                'User-Agent': 'FactFiber-Docs-Lambda',
                'Accept': 'application/vnd.github.v3+json'
            }
        };

        const req = https.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => data += chunk);
            res.on('end', () => {
                if (res.statusCode === 200) {
                    try {
                        resolve(JSON.parse(data));
                    } catch (e) {
                        resolve(null);
                    }
                } else {
                    console.error(`GitHub API error: ${res.statusCode}`);
                    resolve(null);
                }
            });
        });

        req.on('error', (e) => {
            console.error('GitHub API request error:', e);
            resolve(null);
        });

        req.end();
    });
}

async function checkTeamMembership(token, username) {
    // If no specific teams configured, allow any org member
    if (ALLOWED_TEAMS.length === 0) {
        return checkOrgMembership(token, username);
    }

    // Check each allowed team
    for (const team of ALLOWED_TEAMS) {
        const isMember = await checkTeamMembershipForTeam(token, username, team);
        if (isMember) {
            return true;
        }
    }

    return false;
}

async function checkOrgMembership(token, username) {
    return new Promise((resolve) => {
        const options = {
            hostname: 'api.github.com',
            path: `/orgs/${GITHUB_ORG}/members/${username}`,
            method: 'GET',
            headers: {
                'Authorization': `token ${token}`,
                'User-Agent': 'FactFiber-Docs-Lambda',
                'Accept': 'application/vnd.github.v3+json'
            }
        };

        const req = https.request(options, (res) => {
            resolve(res.statusCode === 204);
        });

        req.on('error', (e) => {
            console.error('GitHub API request error:', e);
            resolve(false);
        });

        req.end();
    });
}

async function checkTeamMembershipForTeam(token, username, teamSlug) {
    return new Promise((resolve) => {
        const options = {
            hostname: 'api.github.com',
            path: `/orgs/${GITHUB_ORG}/teams/${teamSlug}/memberships/${username}`,
            method: 'GET',
            headers: {
                'Authorization': `token ${token}`,
                'User-Agent': 'FactFiber-Docs-Lambda',
                'Accept': 'application/vnd.github.v3+json'
            }
        };

        const req = https.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => data += chunk);
            res.on('end', () => {
                if (res.statusCode === 200) {
                    try {
                        const membership = JSON.parse(data);
                        resolve(membership.state === 'active');
                    } catch (e) {
                        resolve(false);
                    }
                } else {
                    resolve(false);
                }
            });
        });

        req.on('error', (e) => {
            console.error('GitHub API request error:', e);
            resolve(false);
        });

        req.end();
    });
}

function generateAuthResponse(originalPath = '/') {
    const authUrl = `https://github.com/login/oauth/authorize?${querystring.stringify({
        client_id: GITHUB_CLIENT_ID,
        scope: 'read:org',
        redirect_uri: 'https://docs.factfiber.ai/auth/callback',
        state: encodeURIComponent(originalPath)
    })}`;

    return {
        status: '302',
        statusDescription: 'Found',
        headers: {
            location: [{
                key: 'Location',
                value: authUrl
            }],
            'cache-control': [{
                key: 'Cache-Control',
                value: 'no-cache, no-store, must-revalidate'
            }]
        }
    };
}

async function handleOAuthCallback(querystring_params) {
    console.log('Processing OAuth callback with params:', querystring_params);

    // Parse query parameters
    const params = querystring.parse(querystring_params);
    const code = params.code;
    const state = params.state;

    if (!code) {
        console.error('No authorization code received');
        return generateErrorResponse();
    }

    try {
        // Exchange authorization code for access token
        const tokenData = await exchangeCodeForToken(code);
        if (!tokenData || !tokenData.access_token) {
            console.error('Failed to exchange code for token');
            return generateErrorResponse();
        }

        // Validate the token and get user info
        const user = await getGitHubUser(tokenData.access_token);
        if (!user) {
            console.error('Failed to get user information');
            return generateErrorResponse();
        }

        // Check team membership
        const isMember = await checkTeamMembership(tokenData.access_token, user.login);
        if (!isMember) {
            console.log(`User ${user.login} is not a member of allowed teams`);
            return generateAccessDeniedResponse();
        }

        // Create success response with authentication cookie
        const redirectUrl = state ? decodeURIComponent(state) : '/';

        return {
            status: '302',
            statusDescription: 'Found',
            headers: {
                location: [{
                    key: 'Location',
                    value: redirectUrl
                }],
                'set-cookie': [{
                    key: 'Set-Cookie',
                    value: `github_token=${tokenData.access_token}; Domain=.factfiber.ai; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age=86400`
                }],
                'cache-control': [{
                    key: 'Cache-Control',
                    value: 'no-cache, no-store, must-revalidate'
                }]
            }
        };

    } catch (error) {
        console.error('OAuth callback error:', error);
        return generateErrorResponse();
    }
}

async function exchangeCodeForToken(code) {
    return new Promise((resolve) => {
        const postData = querystring.stringify({
            client_id: GITHUB_CLIENT_ID,
            client_secret: GITHUB_CLIENT_SECRET,
            code: code
        });

        const options = {
            hostname: 'github.com',
            path: '/login/oauth/access_token',
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Content-Length': Buffer.byteLength(postData),
                'Accept': 'application/json',
                'User-Agent': 'FactFiber-Docs-Lambda'
            }
        };

        const req = https.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => data += chunk);
            res.on('end', () => {
                if (res.statusCode === 200) {
                    try {
                        resolve(JSON.parse(data));
                    } catch (e) {
                        console.error('Failed to parse token response:', e);
                        resolve(null);
                    }
                } else {
                    console.error(`GitHub OAuth error: ${res.statusCode}`);
                    resolve(null);
                }
            });
        });

        req.on('error', (e) => {
            console.error('GitHub OAuth request error:', e);
            resolve(null);
        });

        req.write(postData);
        req.end();
    });
}

function generateAccessDeniedResponse() {
    return {
        status: '403',
        statusDescription: 'Forbidden',
        body: 'Access denied. You must be a member of an authorized team to access this documentation.',
        headers: {
            'content-type': [{
                key: 'Content-Type',
                value: 'text/plain'
            }],
            'cache-control': [{
                key: 'Cache-Control',
                value: 'no-cache, no-store, must-revalidate'
            }]
        }
    };
}

function generateErrorResponse() {
    return {
        status: '500',
        statusDescription: 'Internal Server Error',
        body: 'Authentication service error',
        headers: {
            'content-type': [{
                key: 'Content-Type',
                value: 'text/plain'
            }],
            'cache-control': [{
                key: 'Cache-Control',
                value: 'no-cache, no-store, must-revalidate'
            }]
        }
    };
}
