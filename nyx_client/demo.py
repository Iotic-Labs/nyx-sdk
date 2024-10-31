from nyx_client import NyxClient

c = NyxClient()

with open("test.csv", "rb") as f:
    c.create_data(
        name="MyData4",
        title="SDK upload test binary",
        description="SDK file upload test",
        size=1080,
        genre="ai",
        categories=["cat1", "cat2", "cat3"],
        file=f,
        content_type="text/csv",
        lang="fr",
        preview="col1, col2, col3\naaa, bbb, ccc",
        license_url="https://opensource.org/licenses/MIT",
    )
