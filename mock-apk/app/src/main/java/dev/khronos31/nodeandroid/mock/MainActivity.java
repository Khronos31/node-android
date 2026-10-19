package dev.khronos31.nodeandroid.mock;

import android.app.Activity;
import android.os.Build;
import android.os.Bundle;
import android.system.Os;
import android.util.Log;
import android.graphics.Typeface;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

public final class MainActivity extends Activity {
    private final Button[] buttons = new Button[5];
    private TextView console;

    private static final String TAG = "NodeMock";
    private static final String VERSION_MARKER = "v24.";
    private static final long TIMEOUT_MS = 30000;

    @Override
    public void onCreate(Bundle state) {
        super.onCreate(state);
        int margin = (int) (20 * getResources().getDisplayMetrics().density);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(margin, margin, margin, margin);

        TextView title = new TextView(this);
        title.setText("Node.js 24 Android / N-API Mock");
        title.setTextSize(23);
        root.addView(title);

        TextView about = new TextView(this);
        about.setText("armv7a / arm64 | EPGStationなし | Android TV・スマホ対応\n"
                + "Java ProcessBuilderでNode.js実行ファイルを起動します。");
        about.setTextSize(15);
        about.setPadding(0, margin / 2, 0, margin / 2);
        root.addView(about);

        buttons[0] = new Button(this);
        buttons[0].setText("1. Node --version");
        root.addView(buttons[0]);

        buttons[1] = new Button(this);
        buttons[1].setText("2. Basic JS smoke (fs/crypto/http/spawn)");
        root.addView(buttons[1]);

        buttons[2] = new Button(this);
        buttons[2].setText("3. Native addon smoke (.node / Node-API)");
        root.addView(buttons[2]);

        buttons[3] = new Button(this);
        buttons[3].setText("4. EPG3 native ABI (better-sqlite3 / fs-ext)");
        root.addView(buttons[3]);

        buttons[4] = new Button(this);
        buttons[4].setText("5. EPG3 functional (SQLite/WAL/flock)");
        root.addView(buttons[4]);

        console = new TextView(this);
        console.setTextSize(13);
        console.setTypeface(Typeface.MONOSPACE);
        console.setTextIsSelectable(true);
        console.setText("Select a test. No hardware tuner is needed.");
        console.setPadding(0, margin, 0, margin);
        root.addView(console);

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.addView(root, new ScrollView.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));
        setContentView(scroll);

        buttons[0].setOnClickListener(v -> execute("version"));
        buttons[1].setOnClickListener(v -> execute("basic"));
        buttons[2].setOnClickListener(v -> execute("addon"));
        buttons[3].setOnClickListener(v -> execute("epg3"));
        buttons[4].setOnClickListener(v -> execute("epg3-functional"));
        buttons[0].requestFocus();
    }

    private File saveAsset(String name) throws Exception {
        File dest = new File(getFilesDir(), name);
        try (InputStream src = getAssets().open(name);
             OutputStream dst = new FileOutputStream(dest, false)) {
            byte[] buffer = new byte[8192];
            int count;
            while ((count = src.read(buffer)) != -1) {
                dst.write(buffer, 0, count);
            }
        }
        return dest;
    }

    private void unpackAssetTree(String assetDir, File target) throws Exception {
        String[] children = getAssets().list(assetDir);
        if (children == null || children.length == 0) {
            throw new IllegalStateException("Missing asset directory: " + assetDir);
        }
        if (!target.isDirectory() && !target.mkdirs()) {
            throw new IllegalStateException("Cannot create directory: " + target);
        }
        for (String child : children) {
            if (child.equals(".") || child.equals("..") || child.contains("/")) {
                throw new IllegalStateException("Unsafe asset name: " + child);
            }
            String assetName = assetDir + "/" + child;
            File dst = new File(target, child);
            String[] nested = getAssets().list(assetName);
            if (nested != null && nested.length > 0) {
                unpackAssetTree(assetName, dst);
            } else {
                try (InputStream input = getAssets().open(assetName);
                     OutputStream output = new FileOutputStream(dst, false)) {
                    byte[] buffer = new byte[8192];
                    int length;
                    while ((length = input.read(buffer)) != -1) {
                        output.write(buffer, 0, length);
                    }
                }
            }
        }
    }

    private void linkNativeAddon(File base, String relativePath, String nativeName)
            throws Exception {
        File link = new File(base, relativePath);
        File parent = link.getParentFile();
        if (!parent.isDirectory() && !parent.mkdirs()) {
            throw new IllegalStateException("Cannot make addon directory: " + parent);
        }
        link.delete();
        Os.symlink(requireNativeLibrary(nativeName), link.getAbsolutePath());
    }

    private File prepareEpg3FunctionalModules() throws Exception {
        // APK assets are trusted and compiled from pinned real upstream npm JS.
        File root = new File(getFilesDir(), "epg3-modules");
        unpackAssetTree("epg3-modules", root);
        // Android linker loads only nativeLibraryDir copies, which have .so
        // names. Retain .node symlink names via Node --preserve-symlinks.
        linkNativeAddon(root, "better-sqlite3/better_sqlite3.node",
                "libepg3_better_sqlite3.so");
        linkNativeAddon(root, "fs-ext/build/Release/fs_ext.node",
                "libepg3_fs_ext.so");
        return root;
    }

    private String requireNativeLibrary(String filename) throws Exception {
        File library = new File(getApplicationInfo().nativeLibraryDir, filename);
        if (!library.isFile()) {
            throw new IllegalStateException("Missing native library: " + library);
        }
        return library.getAbsolutePath();
    }

    private String prepareAddonSymlink() throws Exception {
        File library = new File(getApplicationInfo().nativeLibraryDir, "libnapi_smoke.so");
        if (!library.isFile()) {
            throw new IllegalStateException("Missing native N-API addon: " + library);
        }
        File link = new File(getFilesDir(), "napi-smoke.node");
        // Delete the old symlink even if its former target no longer exists
        // (Android changes nativeLibraryDir across installations).
        link.delete();
        Os.symlink(library.getAbsolutePath(), link.getAbsolutePath());
        return link.getAbsolutePath();
    }

    private void toggleButtons(boolean enabled) {
        for (Button button : buttons) button.setEnabled(enabled);
    }

    private void execute(String kind) {
        toggleButtons(false);
        console.setText("Running " + kind + "...");
        new Thread(() -> {
            String output;
            try {
                File binary = new File(getApplicationInfo().nativeLibraryDir, "libnode_exec.so");
                if (!binary.isFile()) {
                    throw new IllegalStateException("Missing Android PIE executable: " + binary);
                }

                List<String> args = new ArrayList<>();
                args.add(binary.getAbsolutePath());
                if ("version".equals(kind)) {
                    args.add("--version");
                } else if ("basic".equals(kind)) {
                    args.add(saveAsset("basic-smoke.js").getAbsolutePath());
                } else if ("epg3-functional".equals(kind)) {
                    args.add("--preserve-symlinks");
                    args.add(saveAsset("epg3-functional-smoke.js").getAbsolutePath());
                } else if ("epg3".equals(kind)) {
                    // Probe the *legacy V8 C++ addon ABI*, not only Node-API.
                    args.add("--preserve-symlinks");
                    args.add(saveAsset("epg3-native-smoke.js").getAbsolutePath());
                } else {
                    // Keep the .node extension so Node uses the native addon loader.
                    args.add("--preserve-symlinks");
                    args.add(saveAsset("native-addon-smoke.js").getAbsolutePath());
                }

                ProcessBuilder builder = new ProcessBuilder(args);
                builder.redirectErrorStream(true);
                builder.directory(getFilesDir());
                builder.environment().put("HOME", getFilesDir().getAbsolutePath());
                builder.environment().put("TMPDIR", getCacheDir().getAbsolutePath());
                builder.environment().put("LD_LIBRARY_PATH", getApplicationInfo().nativeLibraryDir);
                builder.environment().put("NODE_DISABLE_COLORS", "1");
                if ("addon".equals(kind)) {
                    builder.environment().put("NAPI_ADDON_PATH", prepareAddonSymlink());
                } else if ("epg3-functional".equals(kind)) {
                    builder.environment().put("EPG3_MODULES_ROOT",
                            prepareEpg3FunctionalModules().getAbsolutePath());
                    builder.environment().put("EPG3_DATA_DIR", getFilesDir().getAbsolutePath());
                } else if ("epg3".equals(kind)) {
                    builder.environment().put("EPG3_SQLITE_NATIVE",
                            requireNativeLibrary("libepg3_better_sqlite3.so"));
                    builder.environment().put("EPG3_FSEXT_NATIVE",
                            requireNativeLibrary("libepg3_fs_ext.so"));
                }

                Process process = builder.start();
                AtomicBoolean timedOut = new AtomicBoolean(false);
                Thread watchdog = new Thread(() -> {
                    try {
                        Thread.sleep(TIMEOUT_MS);
                        try {
                            process.exitValue();
                        } catch (IllegalThreadStateException stillRunning) {
                            timedOut.set(true);
                            process.destroy();
                        }
                    } catch (InterruptedException stopped) {
                        Thread.currentThread().interrupt();
                    }
                }, "node-timeout");
                watchdog.setDaemon(true);
                watchdog.start();

                StringBuilder text = new StringBuilder();
                try (BufferedReader in = new BufferedReader(new InputStreamReader(
                        process.getInputStream(), StandardCharsets.UTF_8))) {
                    String line;
                    while ((line = in.readLine()) != null) {
                        if (text.length() < 64000) text.append(line).append('\n');
                    }
                }
                int exit = process.waitFor();
                watchdog.interrupt();
                String marker = "version".equals(kind)
                        ? VERSION_MARKER
                        : ("basic".equals(kind) ? "NODE_BASIC_PASS"
                                : ("epg3".equals(kind) ? "EPG3_LEGACY_ADDON_PASS"
                                        : ("epg3-functional".equals(kind) ? "EPG3_FUNCTIONAL_PASS"
                                                : "NODE_ADDON_PASS")));
                boolean ok = exit == 0 && !timedOut.get() && text.indexOf(marker) != -1;

                output = (ok ? "PASS" : "FAIL")
                        + " | test=" + kind
                        + " | exit=" + exit
                        + (timedOut.get() ? " | TIMEOUT" : "")
                        + "\nABI=" + Build.SUPPORTED_ABIS[0]
                        + "\nNode=" + binary.getAbsolutePath()
                        + "\n\n" + text;
                Log.i(TAG, output);
            } catch (Throwable error) {
                output = "FAIL | test=" + kind + "\n" + error;
                Log.e(TAG, "Node test failed: " + kind, error);
            }
            final String result = output;
            runOnUiThread(() -> {
                console.setText(result);
                toggleButtons(true);
            });
        }, "node-mock-" + kind).start();
    }
}
