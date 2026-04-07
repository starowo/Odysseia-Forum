import { describe, expect, it } from 'vitest';
import { sanitizeInternalRedirect } from './navigationSafety';

describe('navigationSafety', () => {
  describe('sanitizeInternalRedirect', () => {
    it('保留合法站内相对路径', () => {
      expect(sanitizeInternalRedirect('/search?q=test#top')).toBe('/search?q=test#top');
    });

    it('对空值回退到首页', () => {
      expect(sanitizeInternalRedirect('')).toBe('/');
      expect(sanitizeInternalRedirect(null)).toBe('/');
      expect(sanitizeInternalRedirect(undefined)).toBe('/');
    });

    it('拒绝外部绝对地址', () => {
      expect(sanitizeInternalRedirect('https://evil.example/steal')).toBe('/');
    });

    it('拒绝协议相对地址与反斜杠路径', () => {
      expect(sanitizeInternalRedirect('//evil.example')).toBe('/');
      expect(sanitizeInternalRedirect('/\\evil')).toBe('/');
    });

    it('拒绝 javascript 协议伪装值', () => {
      expect(sanitizeInternalRedirect('javascript:alert(1)')).toBe('/');
    });
  });
});
