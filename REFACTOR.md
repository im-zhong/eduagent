## useful part

1. ingestion job
2. ui: ingestion_lab.py
3. ui: agent_chat.py
4. ui: api_clien.py, 这个肯定是要写在UI这一部分的，假设我们用typescript，也需要这个功能，但是python提供的东西肯定就没法用了对吧，这样就能得到这个东西的合适的位置就在ui端
5. ui: main.py
6. ui: overview
7. storage: engine, milvus, minio: ~500
8. tools: retrieval: 现在这两个都特别简单，还是挺合适的
9. tools: extractor, 不过后续把这些东西放到对应的模块里面就行了，模块在设计的时候要尽可能减少耦合性，比如schema的定义，相应的数据库表的定义和功能的实现都应该在模块内部，而不是在一个公共的模块，思考的原则就是，我们能不能非常方便的把这个功能所依赖的代码非常简单的去掉？
10. document：这个是有用的，整合了index的部分

最后大概留下三千行代码，~～目前就先做一个基于milvus的rag chat就行了～～~
在不影响现有功能的情况下，把没有用的代码先清理到一个文件夹里面

## useless part

1. unit tests
2. streamlit uis
3. agent manager
4. task: celery, 仔细斟酌celery的必要性，因为他带来了太多的复杂度
    1. 为什么引入celery？因为又一些较长的后台任务，防止阻塞API
    2. 那么在目前来看，只有一个ingestion job是一个比较长的任务，因为涉及到文档转换（pandoc），chunk，embedding，
    3. 我想要去掉celery，首先，celery确实会引入很多的复杂度，所以只有在明确需要的时候才考虑引入，在我们的系统中，目前celery唯一的作用就是做索引，为了这一点点功能引入如此巨大的复杂度，本身就违背了 make it simple原则

直接用AI生成的东西简直就是一坨大垃圾！
耦合的太严重了！
