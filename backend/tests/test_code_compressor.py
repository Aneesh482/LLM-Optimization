"""Unit tests for CodeCompressor (AST skeleton extraction & code structure preservation)."""

from __future__ import annotations

import pytest
from app.services.compressors.code_compressor import CodeCompressor


@pytest.fixture
def compressor() -> CodeCompressor:
    return CodeCompressor()


def test_compress_empty_code(compressor: CodeCompressor):
    res = compressor.compress("")
    assert res.compressed_content == ""
    assert res.content_type == "code"


def test_compress_python_ast_skeleton(compressor: CodeCompressor):
    python_code = """
\"\"\"Module for managing user authentication and security tokens.\"\"\"

import os
import sys
from typing import Optional, List

SECRET_KEY = "xyz123"

class AuthenticationManager:
    \"\"\"Manages tokens and login state.\"\"\"

    def __init__(self, key: str) -> None:
        self.key = key
        self.active_sessions = []
        for i in range(100):
            self.active_sessions.append(f"init_session_{i}")

    async def authenticate_user(self, username: str, password_hash: str) -> bool:
        \"\"\"Verify user credentials.\"\"\"
        if not username or not password_hash:
            return False
        # Do heavy database query and validation
        user = await db.query(username)
        return user is not None and user.check_password(password_hash)

    def revoke_token(self, token_id: str) -> None:
        if token_id in self.active_sessions:
            self.active_sessions.remove(token_id)

def helper_utility_function(data: dict) -> str:
    \"\"\"Helper calculation.\"\"\"
    return str(data)
"""
    res = compressor.compress(python_code, skeleton_only=True)

    assert res.content_type == "code"
    assert res.compression_ratio < 0.8
    assert res.estimated_tokens_saved > 0

    compressed = res.compressed_content
    # Preserves imports
    assert "import os" in compressed
    assert "from typing import Optional, List" in compressed
    # Preserves classes and signatures
    assert "class AuthenticationManager:" in compressed
    assert "def __init__(self, key: str) -> None:" in compressed
    assert "async def authenticate_user(self, username: str, password_hash: str) -> bool:" in compressed
    assert "def revoke_token(self, token_id: str) -> None:" in compressed
    assert "def helper_utility_function(data: dict) -> str:" in compressed

    # Verifies internal loops/details replaced by stubs
    assert "self.active_sessions.append" not in compressed
    assert "..." in compressed


def test_compress_javascript_code(compressor: CodeCompressor):
    js_code = """
import React, { useState, useEffect } from 'react';
import axios from 'axios';

export interface UserProps {
    id: string;
    role: string;
}

export function UserDashboard(props: UserProps) {
    const [data, setData] = useState([]);
    useEffect(() => {
        axios.get('/api/users').then(res => setData(res.data));
    }, []);
    return <div>User list count: {data.length}</div>;
}

export const calculateMetrics = (items: number[]): number => {
    let sum = 0;
    for (let x of items) { sum += x * 2; }
    return sum;
};
"""
    res = compressor.compress(js_code, language="javascript", skeleton_only=True)
    assert res.content_type == "code"
    assert res.compression_ratio < 0.9

    compressed = res.compressed_content
    assert "import React" in compressed
    assert "export function UserDashboard" in compressed
    assert "export interface UserProps" in compressed
