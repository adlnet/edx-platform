(function () {
    'use strict';
    var getModule = function (moduleName, excludeCommonDeps) {
        var module = {
            name: moduleName
        };

        if (!excludeCommonDeps) {
            module.exclude = ['js/pages/common_deps'];
        }

        return module;
    };

    var getModulesList = function (modules) {
        var result = [getModule('js/pages/common_deps', true)];
        return result.concat(modules.map(function (moduleName) {
            return getModule(moduleName);
        }));
    };

    return {
        /**
         * List the modules that will be optimized. All their immediate and deep
         * dependencies will be included in the module's file when the build is
         * done.
         */
        modules: getModulesList([
            'js/pages/asset_index',
            'js/pages/base',
            'js/pages/checklists',
            'js/pages/container',
            'js/pages/course',
            'js/pages/course_create_rerun',
            'js/pages/course_info',
            'js/pages/edit_tabs',
            'js/pages/export',
            'js/pages/group_configurations',
            'js/pages/import',
            'js/pages/index',
            'js/pages/login',
            'js/pages/manage_users',
            'js/pages/outline',
            'js/pages/register',
            'js/pages/settings',
            'js/pages/settings_advanced',
            'js/pages/settings_graders',
            'js/pages/textbooks'
        ]),
        /**
         * By default all the configuration for optimization happens from the command
         * line or by properties in the config file, and configuration that was
         * passed to requirejs as part of the app's runtime "main" JS file is *not*
         * considered. However, if you prefer the "main" JS file configuration
         * to be read for the build so that you do not have to duplicate the values
         * in a separate configuration, set this property to the location of that
         * main JS file. The first requirejs({}), require({}), requirejs.config({}),
         * or require.config({}) call found in that file will be used.
         * As of 2.1.10, mainConfigFile can be an array of values, with the last
         * value's config take precedence over previous values in the array.
         */
        mainConfigFile: 'require-config.js',
        /**
         * Set paths for modules. If relative paths, set relative to baseUrl above.
         * If a special value of "empty:" is used for the path value, then that
         * acts like mapping the path to an empty file. It allows the optimizer to
         * resolve the dependency to path, but then does not include it in the output.
         * Useful to map module names that are to resources on a CDN or other
         * http: URL when running in the browser and during an optimization that
         * file should be skipped because it has no dependencies.
         */
        paths: {
            'gettext': 'empty:',
            'xmodule': 'empty:',
            'mathjax': 'empty:',
            'tender': 'empty:',
            'youtube': 'empty:'
        },
        /**
         * If shim config is used in the app during runtime, duplicate the config
         * here. Necessary if shim config is used, so that the shim's dependencies
         * are included in the build. Using "mainConfigFile" is a better way to
         * pass this information though, so that it is only listed in one place.
         * However, if mainConfigFile is not an option, the shim config can be
         * inlined in the build config.
         */
        shim: {
            'xmodule': {
                deps: [
                    'jquery', 'underscore', 'mathjax', 'codemirror', 'tinymce',
                    'jquery.tinymce', 'jquery.qtip', 'jquery.scrollTo', 'jquery.flot',
                    'jquery.cookie', 'utility'
                ]
            }
        },
        /**
         * Introduced in 2.1.2: If using "dir" for an output directory, normally the
         * optimize setting is used to optimize the build bundles (the "modules"
         * section of the config) and any other JS file in the directory. However, if
         * the non-build bundle JS files will not be loaded after a build, you can
         * skip the optimization of those files, to speed up builds. Set this value
         * to true if you want to skip optimizing those other non-build bundle JS
         * files.
         */
        skipDirOptimize: true,
        /**
         * Introduced in 2.1.2 and considered experimental.
         * If the minifier specified in the "optimize" option supports generating
         * source maps for the minified code, then generate them. The source maps
         * generated only translate minified JS to non-minified JS, it does not do
         * anything magical for translating minified JS to transpiled source code.
         * Currently only optimize: "uglify2" is supported when running in node or
         * rhino, and if running in rhino, "closure" with a closure compiler jar
         * build after r1592 (20111114 release).
         * The source files will show up in a browser developer tool that supports
         * source maps as ".js.src" files.
         */
        generateSourceMaps: true,
        /**
         * Allow CSS optimizations. Allowed values:
         * - "standard": @import inlining and removal of comments, unnecessary
         * whitespace and line returns.
         * Removing line returns may have problems in IE, depending on the type
         * of CSS.
         * - "standard.keepLines": like "standard" but keeps line returns.
         * - "none": skip CSS optimizations.
         * - "standard.keepComments": keeps the file comments, but removes line
         * returns.  (r.js 1.0.8+)
         * - "standard.keepComments.keepLines": keeps the file comments and line
         * returns. (r.js 1.0.8+)
         * - "standard.keepWhitespace": like "standard" but keeps unnecessary whitespace.
         */
        optimizeCss: 'none',
        /**
         * How to optimize all the JS files in the build output directory.
         * Right now only the following values are supported:
         * - "uglify": Uses UglifyJS to minify the code.
         * - "uglify2": Uses UglifyJS2.
         * - "closure": Uses Google's Closure Compiler in simple optimization
         * mode to minify the code. Only available if REQUIRE_ENVIRONMENT is "rhino" (the default).
         * - "none": No minification will be done.
         */
        optimize: 'uglify2',
        /**
         * Sets the logging level. It is a number:
         * TRACE: 0,
         * INFO: 1,
         * WARN: 2,
         * ERROR: 3,
         * SILENT: 4
         * Default is 0.
         */
        logLevel: 4
    };
} ())
