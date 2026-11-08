import React, { useState } from 'react';
import { Shield, Lock, Mail, UserCheck } from 'lucide-react';
import api from '../api/client';

export default function LoginPage({ onLoginSuccess, setActivePage }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const executeLogin = async (loginEmail, loginPassword) => {
    setIsLoading(true);
    setErrorMsg('');
    try {
      const res = await api.post('/auth/login', {
        email: loginEmail,
        password: loginPassword
      });

      const { access_token, user } = res.data;
      localStorage.setItem('relay_token', access_token);
      localStorage.setItem('relay_user', JSON.stringify(user));

      onLoginSuccess(user);
      setActivePage('coordinator');
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Authentication failed. Please check credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCustomSubmit = (e) => {
    e.preventDefault();
    executeLogin(email, password);
  };

  return (
    <div className="max-w-md mx-auto py-12 px-4 space-y-6">
      <div className="text-center space-y-2">
        <div className="inline-flex p-3 bg-emerald-100 text-emerald-800 rounded-2xl">
          <Shield className="w-8 h-8" />
        </div>
        <h1 className="text-2xl font-black text-slate-900">Sign in to RELAY</h1>
        <p className="text-xs text-slate-500">Access coordinator tools, conflict triage, and field operations.</p>
      </div>

      {errorMsg && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl">
          {errorMsg}
        </div>
      )}

      {/* Quick Portfolio Demo Logins */}
      <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200 space-y-2">
        <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
          One-Click Portfolio Demo Roles:
        </div>
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => executeLogin('coordinator@relay.org', 'relay123')}
            className="p-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl text-xs font-bold text-left transition"
          >
            <div>Lead Coordinator</div>
            <div className="text-[10px] text-emerald-400 font-normal">Full conflict triage</div>
          </button>
          <button
            type="button"
            onClick={() => executeLogin('volunteer@relay.org', 'relay123')}
            className="p-2.5 bg-emerald-700 hover:bg-emerald-600 text-white rounded-xl text-xs font-bold text-left transition"
          >
            <div>Field Volunteer</div>
            <div className="text-[10px] text-emerald-200 font-normal">Inventory & status</div>
          </button>
        </div>
      </div>

      {/* Custom Login Form */}
      <form onSubmit={handleCustomSubmit} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div className="space-y-1">
          <label className="text-xs font-bold text-slate-700">Email Address</label>
          <div className="relative">
            <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@relay.org"
              className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-xl text-sm"
            />
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-bold text-slate-700">Password</label>
          <div className="relative">
            <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-xl text-sm"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full bg-slate-900 hover:bg-slate-800 text-white font-bold py-3 rounded-xl text-sm shadow-md transition"
        >
          {isLoading ? 'Authenticating...' : 'Sign In'}
        </button>
      </form>
    </div>
  );
}
