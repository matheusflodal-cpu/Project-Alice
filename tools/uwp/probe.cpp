#define NOMINMAX
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <winapifamily.h>
#if WINAPI_FAMILY != WINAPI_FAMILY_APP
#error This diagnostic must be compiled for the UWP API family.
#endif
#include <d3d11.h>
#include <dxgi1_2.h>
#include <xaudio2.h>
#include <winrt/Windows.ApplicationModel.Core.h>
#include <winrt/Windows.ApplicationModel.Activation.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Storage.h>
#include <winrt/Windows.UI.Core.h>

using namespace winrt;
using namespace Windows::ApplicationModel::Core;
using namespace Windows::UI::Core;

struct Probe : implements<Probe, IFrameworkViewSource, IFrameworkView> {
    CoreWindow window{nullptr};
    bool closed = false;
    com_ptr<ID3D11Device> device;
    com_ptr<ID3D11DeviceContext> context;
    com_ptr<IDXGISwapChain1> swapchain;
    com_ptr<ID3D11RenderTargetView> target;
    com_ptr<IXAudio2> audio;
    IXAudio2MasteringVoice* voice = nullptr;

    ~Probe() { if (voice) voice->DestroyVoice(); }
    IFrameworkView CreateView() { return *this; }
    void Initialize(CoreApplicationView const& view) {
        view.Activated([](auto const&, auto const&) {
            CoreWindow::GetForCurrentThread().Activate();
        });
    }
    void SetWindow(CoreWindow const& value) {
        window = value;
        window.Closed([this](auto const&, auto const&) { closed = true; });
    }
    void Load(hstring const&) {}
    void Uninitialize() {}

    Windows::Foundation::IAsyncAction WriteReport() {
        auto lifetime = get_strong();
        auto folder = Windows::Storage::ApplicationData::Current().LocalFolder();
        auto file = co_await folder.CreateFileAsync(L"uwp-probe.txt",
            Windows::Storage::CreationCollisionOption::ReplaceExisting);
        co_await Windows::Storage::FileIO::WriteTextAsync(file,
            L"Project Alice UWP platform probe; NOT THE GAME.\r\n"
            L"CoreWindow, D3D11 swap chain, XAudio2 mastering voice: initialized.\r\n"
            L"LocalState write: successful.\r\n");
    }

    void Run() {
        check_hresult(D3D11CreateDevice(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr,
            D3D11_CREATE_DEVICE_BGRA_SUPPORT, nullptr, 0, D3D11_SDK_VERSION,
            device.put(), nullptr, context.put()));
        auto dxgi = device.as<IDXGIDevice>();
        com_ptr<IDXGIAdapter> adapter;
        check_hresult(dxgi->GetAdapter(adapter.put()));
        com_ptr<IDXGIFactory2> factory;
        check_hresult(adapter->GetParent(__uuidof(IDXGIFactory2), factory.put_void()));
        DXGI_SWAP_CHAIN_DESC1 desc{};
        desc.Width = 1280;
        desc.Height = 720;
        desc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
        desc.SampleDesc.Count = 1;
        desc.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
        desc.BufferCount = 2;
        desc.SwapEffect = DXGI_SWAP_EFFECT_FLIP_SEQUENTIAL;
        desc.Scaling = DXGI_SCALING_STRETCH;
        check_hresult(factory->CreateSwapChainForCoreWindow(device.get(),
            reinterpret_cast<::IUnknown*>(get_abi(window)), &desc, nullptr, swapchain.put()));
        com_ptr<ID3D11Texture2D> buffer;
        check_hresult(swapchain->GetBuffer(0, __uuidof(ID3D11Texture2D), buffer.put_void()));
        check_hresult(device->CreateRenderTargetView(buffer.get(), nullptr, target.put()));
        check_hresult(XAudio2Create(audio.put(), 0, XAUDIO2_DEFAULT_PROCESSOR));
        check_hresult(audio->CreateMasteringVoice(&voice));
        auto report = WriteReport();
        while (!closed) {
            window.Dispatcher().ProcessEvents(CoreProcessEventsOption::ProcessAllIfPresent);
            if (report && report.Status() != Windows::Foundation::AsyncStatus::Started) {
                report.GetResults();
                report = nullptr;
            }
            if (!window.Visible()) {
                window.Dispatcher().ProcessEvents(CoreProcessEventsOption::ProcessOneAndAllPending);
                continue;
            }
            constexpr float color[] = {0.04f, 0.16f, 0.30f, 1.0f};
            context->ClearRenderTargetView(target.get(), color);
            check_hresult(swapchain->Present(1, 0));
        }
    }
};

int __stdcall wWinMain(HINSTANCE, HINSTANCE, wchar_t*, int) {
    try {
        init_apartment(apartment_type::single_threaded);
        CoreApplication::Run(make<Probe>());
        return 0;
    } catch (hresult_error const& error) {
        OutputDebugStringW(error.message().c_str());
        return 1;
    }
}
