'use strict';

const https = require('https');
const querystring = require('querystring');

// Environment variables
const GITHUB_CLIENT_ID = process.env.GITHUB_CLIENT_ID;
const GITHUB_CLIENT_SECRET = process.env.GITHUB_CLIENT_SECRET;
const GITHUB_ORG = process.env.GITHUB_ORG;
const ALLOWED_TEAMS = process.env.ALLOWED_TEAMS ? process.env.ALLOWED_TEAMS.split(',') : [];
const PUBLIC_PATHS = process.env.PUBLIC_PATHS ? process.env.PUBLIC_PATHS.split(',') : ['/'];

// Cache for GitHub API responses (5 minute TTL)
const cache = new Map();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

exports.handler = async (event) => {
    const request = event.Records[0].cf.request;
    const headers = request.headers;
    const uri = request.uri;

    console.log(`Processing request for: ${uri}`);

    // Check if path is public
    if (isPublicPath(uri)) {
        console.log(`Public path: ${uri}`);
        return request;
    }

    // Check for authentication token
    const authToken = getAuthToken(headers);
    if (!authToken) {
        console.log('No auth token found');
        return generateAuthResponse();
    }

    try {
        // Validate GitHub token and check team membership
        const isValid = await validateGitHubToken(authToken);
        if (isValid) {
            console.log('Valid authentication');
            return request;
        } else {
            console.log('Invalid authentication');
            return generateAuthResponse();
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

function generateAuthResponse() {
    const authUrl = `https://github.com/login/oauth/authorize?${querystring.stringify({
        client_id: GITHUB_CLIENT_ID,
        scope: 'read:org',
        redirect_uri: 'https://docs.factfiber.ai/auth/callback'
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
