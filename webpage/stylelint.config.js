export default {
  extends: ['stylelint-config-standard', 'stylelint-config-standard-scss'],
  plugins: ['stylelint-order'],
  ignoreFiles: ['dist/**/*', 'node_modules/**/*'],
  rules: {
    'at-rule-no-unknown': null,
    'scss/at-rule-no-unknown': null,
    'no-descending-specificity': null,
    'selector-class-pattern': null,
    'custom-property-pattern': null,
    'declaration-block-no-redundant-longhand-properties': null,
    'declaration-empty-line-before': null,
    'property-no-vendor-prefix': null,
    'media-feature-range-notation': null,
    'color-function-alias-notation': null,
    'color-function-notation': null,
    'alpha-value-notation': null,
    'font-family-name-quotes': null,
    'value-keyword-case': null,
    'at-rule-empty-line-before': null,
    'order/order': [
      'custom-properties',
      'dollar-variables',
      {
        type: 'at-rule',
        name: 'apply',
      },
      'declarations',
      'rules',
    ],
  },
  overrides: [
    {
      files: ['src/**/*.tsx'],
      customSyntax: 'postcss-html',
    },
    {
      files: ['src/shared/styles/globals.css'],
      rules: {
        'no-invalid-position-at-import-rule': null,
      },
    },
  ],
};
